# meds2rdf/sinks/graph_sink.py
from __future__ import annotations

from collections.abc import Iterable

from rdflib import Graph, URIRef

from meds2rdf.sinks.base import Triple, TripleSink


class GraphSink(TripleSink):
    """Buffered sink that writes triples into an `rdflib.Graph`.

    This sink buffers triples in memory and periodically flushes them into
    the provided `rdflib.Graph` using `graph.addN`, which is efficient for
    bulk insertion.

    Parameters
    ----------
    graph:
        An existing `rdflib.Graph` instance to receive triples.
    batch_size:
        Number of triples to buffer before flushing into the Graph. Choose
        a value that balances memory use and throughput (e.g. 50_000–500_000).
    """

    def __init__(self, graph: Graph, batch_size: int = 64_000):
        self.graph = graph
        self.batch_size = int(batch_size)
        self._buffer: list[Triple] = []

    def add(self, s: URIRef, p: URIRef, o: URIRef) -> None:
        """Buffer one triple and flush if the buffer limit is reached."""
        self._buffer.append((s, p, o))
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def add_many(self, triples: Iterable[Triple]) -> None:
        """Buffer many triples in one call and flush if needed."""
        self._buffer.extend(triples)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Flush buffered triples into the rdflib.Graph using addN."""
        if not self._buffer:
            return
        self.graph.addN((s, p, o, self.graph) for s, p, o in self._buffer)
        self._buffer.clear()

    def close(self) -> None:
        """Final flush; Graph itself remains available to caller."""
        self.flush()
