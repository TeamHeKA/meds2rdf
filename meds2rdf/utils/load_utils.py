from pathlib import Path
from typing import Any, Callable
import polars as pl
import json

BATCH_SIZE = 100000

def on_parquet(files_path: list[Path], run: Callable[[pl.DataFrame], Any]):
    data = pl.scan_parquet(files_path)
    for batch in data.collect(engine="streaming").iter_slices(n_rows=BATCH_SIZE):
        run(batch)

def raise_if_not_exist(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name.capitalize()} not found at: {path}.\n"
            f"You set 'include_{path.name}=True', but it does not exist."
        )
    
def load_json(path: Path):
    with open(path) as f:
        return json.load(f)