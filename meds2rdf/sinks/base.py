# meds2rdf/sinks/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from rdflib import URIRef

Triple = tuple[URIRef, URIRef, URIRef]


class TripleSink(ABC):
    """Abstract base class for streaming RDF triple sinks.

    A TripleSink receives RDF triples produced by the conversion pipeline
    and persists them (or forwards them) in a sink-specific way.

    Subclasses should implement `add`, `add_many`, and `flush`. `close`
    calls `flush()` by default and may be overridden for additional cleanup.

    The design goals for sinks:
      * Be storage-agnostic (in-memory graph, file, HTTP endpoint, message bus).
      * Support both single-triple writes (`add`) and bulk writes (`add_many`)
      * Support efficient batched flushes to improve throughput.

    Notes
    -----
    * Triples are expressed as native `rdflib` terms (for example `URIRef`,
      `Literal`, etc.). Using rdflib terms ensures correct N-Triples
      serialization when sinks call `node.n3()`.
    * Implementations should be robust to being called from streaming pipelines
      and should not keep unbounded memory (use internal buffering with config).
    """

    @abstractmethod
    def add(self, s: URIRef, p: URIRef, o: URIRef) -> None:
        """Add a single triple to the sink buffer.

        This should be lightweight and able to be called frequently by streaming
        mappers. Implementations may buffer triples and flush when a buffer
        threshold is reached.

        Args:
            s: Subject term (rdflib term).
            p: Predicate term (rdflib term).
            o: Object term (rdflib term).
        """

    @abstractmethod
    def add_many(self, triples: Iterable[Triple]) -> None:
        """Add an iterable of triples to the sink in bulk.

        Bulk ingestion enables sinks to optimize insertion (for example,
        call `graph.addN` or write a chunk to disk).

        Args:
            triples: Iterable of `(s, p, o)` rdflib term tuples.
        """

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered triples to the underlying storage.

        After `flush` completes, sinks should have persisted all buffered
        triples and cleared internal buffers. Calling `flush` repeatedly
        without new triples should be a no-op.
        """

    def close(self) -> None:
        """Optional cleanup and final flush.

        Default implementation flushes any buffered triples. Subclasses
        may override to perform additional cleanup (close files, release
        network resources, etc.).
        """
        self.flush()
