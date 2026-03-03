# meds2rdf/sinks/ntriples_sink.py
from __future__ import annotations

import gzip
from collections.abc import Iterable
from pathlib import Path

from rdflib import URIRef

from meds2rdf.sinks.base import Triple, TripleSink


class NTriplesSink(TripleSink):
    """
    Buffered N-Triples (NT) file sink with optional gzip compression.

    that writes into multiple files inside a target directory.

    Files are named:

        part-00000.nt.gz
        part-00001.nt.gz
        part-00002.nt.gz
        ...

    Rotation occurs after `max_triples_per_file`. It buffers triples
    to reduce syscall overhead and to increase throughput.

    Parameters
    ----------
     output_dir : Path
        Directory where part files will be created. If `gzip_mode=True`
        the file will be a gzip compressed `.nt.gz` file.
    batch_size:
        Number of triples to buffer before calling `flush`.
    gzip_mode:
        If True, open the destination file using gzip compression.

    Notes
    -----
    * The sink uses `node.n3()` to serialize rdflib terms so that Literals,
      base URIs and language/datatype information are preserved.
    * The sink will create parent directories of `path` automatically.
    """

    def __init__(
        self,
        output_dir: Path,
        batch_size: int = 200_000,
        gzip_mode: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.batch_size = batch_size
        self.max_triples_per_file = 1_000_000
        self.gzip_mode = gzip_mode

        self._buffer: list[Triple] = []
        self._file_index = 0
        self._triples_in_current_file = 0
        self._file = None

        self._open_new_file()

    # --------------------------------------------------
    # File handling
    # --------------------------------------------------

    def _build_filename(self) -> Path:
        suffix = ".nt.gz" if self.gzip_mode else ".nt"
        return self.output_dir / f"part-{self._file_index:05d}{suffix}"

    def _open_new_file(self):
        if self._file:
            self._file.close()

        file_path = self._build_filename()

        if self.gzip_mode:
            self._file = gzip.open(file_path, "wt", encoding="utf-8")
        else:
            self._file = open(file_path, "w", encoding="utf-8")

        self._triples_in_current_file = 0
        self._file_index += 1

    # --------------------------------------------------
    # Sink API
    # --------------------------------------------------

    def add(self, s: URIRef, p: URIRef, o: URIRef) -> None:
        self._buffer.append((s, p, o))
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def add_many(self, triples: Iterable[Triple]) -> None:
        self._buffer.extend(triples)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return

        if not self._file:
            raise FileExistsError("There was an error during file opening.")

        write = self._file.write

        for s, p, o in self._buffer:
            write(f"{s.n3()} {p.n3()} {o.n3()} .\n")
            self._triples_in_current_file += 1

            if self._triples_in_current_file >= self.max_triples_per_file:
                self._open_new_file()

        self._buffer.clear()

    def close(self) -> None:
        self.flush()
        if self._file:
            self._file.close()
