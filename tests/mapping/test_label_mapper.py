from pathlib import Path

from rdflib import Graph, URIRef, Literal, XSD
from meds2rdf.mapping.label_mapper import map_label_df
from meds2rdf.utils.load_utils import load_and_parse_meds_table2
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
import polars as pl

def test_map_label_table_adds_labelsample_triples(tmp_path):
    graph = Graph()
    
    labels = pl.DataFrame([
        {"subject_id": 1, "prediction_time": "2025-01-01T00:00:00"},
        {"subject_id": 2, "prediction_time": "2025-01-01T00:00:00"}
    ])
    
    path = Path(tmp_path / "data.parquet")
    labels.write_parquet(path)

    load_and_parse_meds_table2(
        files_path=[path],
        entity="Label",
        map=map_label_df,
        storage=graph,
        provenance=None
    )

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])

    assert (MEDS_INSTANCES["label/1_0"], None, MEDS.LabelSample) in graph
    assert (MEDS_INSTANCES["label/1_0"], MEDS.hasSubject, subj_uri) in graph
    assert (MEDS_INSTANCES["label/1_0"], MEDS.predictionTime, Literal(labels[0, "prediction_time"], datatype=XSD.dateTime)) in graph
    assert (MEDS_INSTANCES["label/2_1"], MEDS.predictionTime, Literal(labels[1, "prediction_time"], datatype=XSD.dateTime)) in graph
