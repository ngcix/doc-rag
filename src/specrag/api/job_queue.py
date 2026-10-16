"""In-process background job queue for index writes.

A single worker serializes ingest and delete jobs so they never race on the
vector store. Job history is in memory and lost on restart.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Job:
    kind: str
    target: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobQueue:
    def __init__(self, max_history: int = 200):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="specrag-job")
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._max_history = max_history

    def submit(self, kind: str, target: str, fn: Callable[[], dict[str, Any]]) -> Job:
        job = Job(kind=kind, target=target)
        with self._lock:
            self._jobs[job.id] = job
            self._prune()
        self._executor.submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: Callable[[], dict[str, Any]]) -> None:
        job.status, job.started_at = "running", time.time()
        try:
            job.result = fn()
            job.status = "succeeded"
        except Exception as exc:
            logger.exception("Job %s (%s %s) failed", job.id, job.kind, job.target)
            job.error = str(exc) or type(exc).__name__
            job.status = "failed"
        finally:
            job.finished_at = time.time()

    def _prune(self) -> None:
        finished = [job_id for job_id, job in self._jobs.items() if job.finished_at is not None]
        for job_id in finished[: max(0, len(self._jobs) - self._max_history)]:
            del self._jobs[job_id]

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(reversed(self._jobs.values()))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
