"""meds2rdf: MEDS -> RDF conversion utilities."""

from importlib.metadata import version as get_version

from .config import Config, MEDSSchema, SemanticMode
from .converter import MedsRDFConverter
from .sinks import GraphSink, NTriplesSink, TripleSink

__all__ = [
    "MedsRDFConverter",
    "Config",
    "MEDSSchema",
    "GraphSink",
    "NTriplesSink",
    "TripleSink",
    "SemanticMode",
]

__version__ = get_version("meds2rdf")
