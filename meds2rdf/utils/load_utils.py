from pathlib import Path
from typing import Any, Callable
import polars as pl

BATCH_SIZE = 100000

def on_parquet(files_path: list[Path], run: Callable[[pl.DataFrame], Any]):
    data = pl.scan_parquet(files_path)
    for batch in data.collect(engine="streaming").iter_slices(n_rows=BATCH_SIZE):
        run(batch)