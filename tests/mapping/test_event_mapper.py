from pathlib import Path

from rdflib import XSD, Graph, URIRef, Literal
from meds2rdf.mapping.event_mapper import map_event
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.utils.load_utils import load_and_parse_meds_table
import polars as pl

def test_map_data_table_adds_event_triples(tmp_path):
    graph: Graph = Graph()
    
    data = pl.DataFrame([
        {"subject_id": 1, "time": "2025-01-01T00:00:00", "code": "CODE1",
         "numeric_value": 42.0, "text_value": "POS"},
        {"subject_id": 2, "time": "2025-01-01T00:00:00", "code": "CODE2"}
    ])
    
    path = Path(tmp_path / "data.parquet")
    data.write_parquet(path)

    # Pass list[Path] as expected
    load_and_parse_meds_table(
        files_path=[path],
        entity="Event",
        map=map_event,
        storage=graph,
        provenance=None
    )

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])
    
    # Example checks (adjust according to your mapper implementation)
    assert (MEDS_INSTANCES["event/1_0"], MEDS.hasSubject, subj_uri) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.codeString, Literal("CODE1", datatype=XSD.string)) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.numericValue, Literal(42.0, datatype=XSD.double)) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.textValue, Literal("POS", datatype=XSD.string)) in graph


    code1_uri = URIRef(MEDS_INSTANCES["code/CODE1"])

    assert (code1_uri, MEDS.codeString, Literal("CODE1", datatype=XSD.string)) in graph
    assert (MEDS_INSTANCES["event/1_0"], MEDS.hasCode, code1_uri) in graph

    assert (MEDS_INSTANCES["event/2_1"], None, MEDS.Event) in graph