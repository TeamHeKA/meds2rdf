import polars as pl
from rdflib import XSD, Graph, Literal, URIRef

from meds2rdf.config import SemanticMode
from meds2rdf.mapping.event_mapper import map_event_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.utils import map_on_load

SAMPLES = pl.DataFrame(
    [
        {
            "subject_id": 1,
            "time": "2025-01-01T00:00:00",
            "code": "SAMPLE_CODE//1",
            "numeric_value": 42.0,
            "text_value": "POS",
        },
        {"subject_id": 2, "time": "2025-01-01T00:00:00", "code": "SAMPLE_CODE//2"},
    ]
)


def _gen_data(data):
    yield data.lazy()


def test_map_data_table_adds_event_triples(tmp_path):
    graph: Graph = Graph()

    # path = Path(tmp_path / "data.parquet")
    sink = GraphSink(graph)
    # data.write_parquet(path)

    # Pass list[Path] as expected
    map_on_load(
        data=_gen_data(SAMPLES),
        entity="Event",
        map_fn=map_event_df,
        sink=sink,
        provenance=None,
        batch_size=100,
    )

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])

    sink.close()

    # Example checks (adjust according to your mapper implementation)
    assert (MEDS_INSTANCES["event/1_0"], MEDS.hasSubject, subj_uri) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.codeString,
        Literal("SAMPLE_CODE//1", datatype=XSD.string),
    ) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.numericValue,
        Literal(42.0, datatype=XSD.double),
    ) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.textValue,
        Literal("POS", datatype=XSD.string),
    ) in graph

    code1_uri = URIRef(MEDS_INSTANCES["code/SAMPLE_CODE_1"])

    assert (code1_uri, MEDS.codeString, Literal("SAMPLE_CODE//1", datatype=XSD.string)) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.hasCode, code1_uri) in graph

    assert (MEDS_INSTANCES["event/2_1"], None, MEDS.Event) in graph


def test_map_data_table_adds_event_triples_partial_mode(tmp_path):
    graph: Graph = Graph()

    # path = Path(tmp_path / "data.parquet")
    sink = GraphSink(graph)
    # data.write_parquet(path)

    # Pass list[Path] as expected
    map_on_load(
        data=_gen_data(SAMPLES),
        entity="Event",
        map_fn=map_event_df,
        sink=sink,
        provenance=None,
        batch_size=100,
        mode=SemanticMode.PARTIAL,
    )

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])

    sink.close()

    # Example checks (adjust according to your mapper implementation)
    assert (subj_uri, MEDS.hasSampleCode, MEDS_INSTANCES["event/1_0"]) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.codeString,
        Literal("SAMPLE_CODE//1", datatype=XSD.string),
    ) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.numericValue,
        Literal(42.0, datatype=XSD.double),
    ) in graph
    assert (
        MEDS_INSTANCES["event/1_0"],
        MEDS.textValue,
        Literal("POS", datatype=XSD.string),
    ) in graph

    code1_uri = URIRef(MEDS_INSTANCES["code/SAMPLE_CODE_1"])

    assert (code1_uri, MEDS.codeString, Literal("SAMPLE_CODE//1", datatype=XSD.string)) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.hasCode, code1_uri) in graph

    assert (MEDS_INSTANCES["event/2_1"], None, MEDS.Event) in graph
