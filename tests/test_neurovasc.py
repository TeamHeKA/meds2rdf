# tests/test_shacl_validation.py
from meds2rdf.converter import MedsRDFConverter
from meds2rdf.utils.rdf_utils import run_shacl_validation


def test_neurovasc_conversion(tmp_path):
    """
    Tests that the output RDF graph from MedsRDFConverter conforms to the MEDS SHACL shapes.
    """

    SHACL_SHAPES_URL = "https://raw.githubusercontent.com/TeamHeKA/meds-ontology/refs/tags/v1.0.2/shacl/meds-shapes.ttl"

    engine = MedsRDFConverter("/home/ubuntu/workspace/meds-to-owl-examples/NEUROVASC/MEDS_cohort")

    data_graph = None
    # Context manager ensures automatic cleanup
    with engine:
        data_graph = engine.convert(
            include_dataset_metadata=True,
            include_codes=True,
            include_labels=False,
            include_splits=True,
            output_dir=tmp_path,
        )

    if data_graph is not None:
        run_shacl_validation(data_graph, SHACL_SHAPES_URL)
