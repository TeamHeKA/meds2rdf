"""meds2rdf: MEDS -> RDF conversion utilities."""


from .converter import MedsRDFConverter
from importlib.metadata import version as get_version

__all__ = ["MedsRDFConverter"]

__version__ = get_version("meds2rdf")