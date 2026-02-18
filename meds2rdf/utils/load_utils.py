from pathlib import Path
from typing import Any, Callable
import polars as pl

def on_parquet(files_path: list[Path], run: Callable[[pl.DataFrame], Any]):
    data = pl.scan_parquet(files_path)
    for batch in data.collect(engine="streaming").iter_slices(n_rows=100_000):
        run(batch)