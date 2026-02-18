from rdflib import XSD, Graph, URIRef, Literal, Namespace
from meds2rdf.mapping.event_mapper import map_data_table
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
import polars as pl

def test_map_data_table_adds_event_triples():
    graph = Graph()
    
    data = pl.DataFrame([
        {"subject_id": 1, "time": "2025-01-01T00:00:00", "code": "CODE1",
         "numeric_value": 42.0, "text_value": "POS"},
        {"subject_id": 2, "time": "2025-01-01T00:00:00", "code": "CODE2"}
    ])
    
    event_uris = map_data_table(graph, data, dataset_uri=None)

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])
    
    # Example checks (adjust according to your mapper implementation)
    assert (event_uris[0], MEDS.hasSubject, subj_uri) in graph
    assert (event_uris[0], MEDS.codeString, Literal("CODE1", datatype=XSD.string)) in graph
    assert (event_uris[0], MEDS.numericValue, Literal(42.0, datatype=XSD.double)) in graph
    assert (event_uris[0], MEDS.textValue, Literal("POS", datatype=XSD.string)) in graph


    code1_uri = URIRef(MEDS_INSTANCES["code/CODE1"])

    assert (code1_uri, MEDS.codeString, Literal("CODE1", datatype=XSD.string)) in graph
    assert (event_uris[0], MEDS.hasCode, code1_uri) in graph

    assert (event_uris[1], None, MEDS.Event) in graph