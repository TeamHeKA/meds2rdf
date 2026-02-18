from rdflib import Graph, URIRef, Literal, XSD
from meds2rdf.mapping.label_mapper import map_label_table
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
import polars as pl

def test_map_label_table_adds_labelsample_triples():
    graph = Graph()
    
    labels = pl.DataFrame([
        {"subject_id": 1, "prediction_time": "2025-01-01T00:00:00"},
        {"subject_id": 2, "prediction_time": "2025-01-01T00:00:00"}
    ])
    
    label_uris = map_label_table(graph, labels, dataset_uri=None)

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])

    assert (label_uris[0], None, MEDS.LabelSample) in graph
    assert (label_uris[0], MEDS.hasSubject, subj_uri) in graph
    assert (label_uris[0], MEDS.predictionTime, Literal(labels[0, "prediction_time"], datatype=XSD.dateTime)) in graph
    assert (label_uris[1], MEDS.predictionTime, Literal(labels[1, "prediction_time"], datatype=XSD.dateTime)) in graph
