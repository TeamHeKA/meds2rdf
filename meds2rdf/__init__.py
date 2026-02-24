"""meds2rdf: MEDS -> RDF conversion utilities."""

from importlib.metadata import version as get_version

from .converter import MedsRDFConverter

__all__ = ["MedsRDFConverter"]

__version__ = get_version("meds2rdf")
