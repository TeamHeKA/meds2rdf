# Optional: expose utility functions
from .base import TripleSink
from .graph_sink import GraphSink
from .nt_file_sink import NTriplesSink

__all__ = ["TripleSink", "GraphSink", "NTriplesSink"]
