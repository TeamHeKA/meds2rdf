# meds2rdf/sinks/ntriples_sink.py
from __future__ import annotations

import gzip
from collections.abc import Iterable
from pathlib import Path

from rdflib import URIRef

from meds2rdf.sinks.base import Triple, TripleSink


class NTriplesSink(TripleSink):
    """Buffered N-Triples (NT) file sink with optional gzip compression.

    This sink writes triples in N-Triples format to a file. It buffers triples
    to reduce syscall overhead and to increase throughput.

    Parameters
    ----------
    path:
        Destination file path. If `gzip_mode=True` the file will be a gzip
        compressed `.nt.gz` file.
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

    def __init__(self, path: Path, batch_size: int = 64_000, gzip_mode: bool = False):
        self.path = Path(path)
        self.batch_size = int(batch_size)
        self.gzip_mode = bool(gzip_mode)
        self._buffer: list[Triple] = []

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.gzip_mode:
            self._file = gzip.open(self.path, "wt", encoding="utf-8")
        else:
            self._file = open(self.path, "w", encoding="utf-8")

    def add(self, s: URIRef, p: URIRef, o: URIRef) -> None:
        """Buffer a triple and flush if buffer is full."""
        self._buffer.append((s, p, o))
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def add_many(self, triples: Iterable[Triple]) -> None:
        """Buffer many triples and flush if the buffer exceeds the batch size."""
        self._buffer.extend(triples)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Write buffered triples to the file in N-Triples format."""
        if not self._buffer:
            return
        write = self._file.write
        # Serialize using n3() so rdflib's escaping and datatype/language info is preserved.
        for s, p, o in self._buffer:
            write(f"{s.n3()} {p.n3()} {o.n3()} .\n")
        self._buffer.clear()

    def close(self) -> None:
        """Flush and close the underlying file object."""
        self.flush()
        try:
            self._file.close()
        except Exception:
            # Best-effort close; callers should manage file existence and permissions.
            pass
