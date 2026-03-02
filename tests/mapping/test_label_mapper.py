import polars as pl
from rdflib import XSD, Graph, Literal, URIRef

from meds2rdf.mapping.label_mapper import map_label_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.utils import map_on_load


def test_map_label_table_adds_labelsample_triples(tmp_path):
    graph = Graph()

    labels = pl.DataFrame(
        [
            {"subject_id": 1, "prediction_time": "2025-01-01T00:00:00"},
            {"subject_id": 2, "prediction_time": "2025-01-01T00:00:00"},
        ]
    )

    # path = Path(tmp_path / "data.parquet")
    sink = GraphSink(graph)
    # labels.write_parquet(path)

    map_on_load(
        data=labels.lazy(),
        entity="Label",
        map_fn=map_label_df,
        sink=sink,
        provenance=None,
        batch_size=100,
    )

    subj_uri = URIRef(MEDS_INSTANCES["subject/1"])

    assert (MEDS_INSTANCES["label/1_0"], None, MEDS.LabelSample) in graph
    assert (MEDS_INSTANCES["label/1_0"], MEDS.hasSubject, subj_uri) in graph
    assert (
        MEDS_INSTANCES["label/1_0"],
        MEDS.predictionTime,
        Literal(labels[0, "prediction_time"], datatype=XSD.dateTime),
    ) in graph
    assert (
        MEDS_INSTANCES["label/2_1"],
        MEDS.predictionTime,
        Literal(labels[1, "prediction_time"], datatype=XSD.dateTime),
    ) in graph
