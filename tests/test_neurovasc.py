# tests/test_shacl_validation.py
from rdflib import Graph

from meds2rdf.config import Config, MEDSSchema
from meds2rdf.converter import MedsRDFConverter
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.sinks.nt_file_sink import NTriplesSink
from meds2rdf.utils.rdf_utils import run_shacl_validation


def test_neurovasc_conversion(tmp_path):
    """
    Tests that the output RDF graph from MedsRDFConverter conforms to the MEDS SHACL shapes.
    """

    SHACL_SHAPES_URL = "https://raw.githubusercontent.com/TeamHeKA/meds-ontology/refs/tags/v1.0.2/shacl/meds-shapes.ttl"

    engine = MedsRDFConverter("/home/ubuntu/workspace/meds-to-owl-examples/NEUROVASC/MEDS_cohort")

    data_graph = Graph()
    cfg = Config(schemas={MEDSSchema.DATASET_METADATA, MEDSSchema.CODES, MEDSSchema.SPLITS})

    engine.convert(
        sink=GraphSink(data_graph),
        cfg=cfg,
    )

    if data_graph is not None:
        run_shacl_validation(data_graph, SHACL_SHAPES_URL)

    engine.convert(sink=NTriplesSink(tmp_path, gzip_mode=True), cfg=cfg)

    assert tmp_path.glob("*.nt.gz").__next__()
