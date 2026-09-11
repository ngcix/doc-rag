"""Sequence chart rendering."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from specrag.sequence_chart.models import SequenceChart

logger = logging.getLogger(__name__)


def render_chart(
    chart: SequenceChart,
    output_file: Path,
) -> bool:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        if _render_mermaid(chart, output_file):
            return True
    except (OSError, subprocess.SubprocessError):
        logger.exception("Mermaid rendering failed")
    return _render_placeholder(chart, output_file)


def _render_mermaid(chart: SequenceChart, output_file: Path) -> bool:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".mmd",
        delete=False,
        encoding="utf-8",
    ) as source:
        source.write(chart.raw_content)
        temporary_path = Path(source.name)
    try:
        result = subprocess.run(
            ["mmdc", "-i", str(temporary_path), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0
    finally:
        temporary_path.unlink(missing_ok=True)


def _render_placeholder(chart: SequenceChart, output_file: Path) -> bool:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow unavailable; cannot render chart placeholder")
        return False

    image = Image.new("RGB", (800, 600), color="white")
    draw = ImageDraw.Draw(image)
    offset = 20
    if chart.title:
        draw.text((20, offset), f"Sequence: {chart.title}", fill="black")
        offset += 30
    draw.text(
        (20, offset),
        f"Participants: {', '.join(chart.participants)}",
        fill="gray",
    )
    offset += 40
    for index, element in enumerate(chart.elements[:10]):
        text = f"{element.source} -> {element.target}: {element.message}" if element.element_type == "message" else f"[{element.element_type}] {element.description or ''}"
        draw.text((40, offset + index * 25), text[:60], fill="black")
    image.save(str(output_file))
    return True
