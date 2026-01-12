from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os

class Processor:
    def __init__(self, max_workers: int = None): # type: ignore
        self.max_workers = max_workers or (os.cpu_count() // 4)  # type: ignore
        print(f"Using {self.max_workers} workers / {os.cpu_count()} cores")

    def run_parallel(self, desc, func, size):
        batch_size = min(self.max_workers, size)
        with tqdm(total=size, desc=desc) as pbar:
            for i in range(0, size, batch_size):
                indices = range(i, min(i + batch_size, size))
                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [executor.submit(func, p) for p in indices]
                    for future in futures:
                        future.result()
                        pbar.update(1)

    def run_sequential(self, desc, func, size):
        with tqdm(total=size, desc=desc) as pbar:
            for p in range(size):
                func(p)
                pbar.update(1)


_processor = None


def get_processor() -> Processor:
    global _processor
    if _processor is None:
        _processor = Processor()
    return _processor
