import polars as pl
from pytest import raises
from rdflib import Graph, URIRef

from meds2rdf.mapping.split_mapper import map_split_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.utils import map_on_load


def test_map_split_table_adds_subjectsplit_triples(tmp_path):
    graph = Graph()

    splits = pl.DataFrame(
        [
            {"subject_id": 1, "split": "train"},
            {"subject_id": 2, "split": "held_out"},
            {"subject_id": 3, "split": "tuning"},
        ]
    )

    sink = GraphSink(graph)

    map_on_load(
        data=splits.lazy(),
        entity="Split",
        map_fn=map_split_df,
        sink=sink,
        provenance=None,
        batch_size=100,
    )

    subj_uris = [
        URIRef(MEDS_INSTANCES["subject/1"]),
        URIRef(MEDS_INSTANCES["subject/2"]),
        URIRef(MEDS_INSTANCES["subject/3"]),
    ]

    sink.flush()

    # Basic assertions
    assert (subj_uris[0], MEDS.assignedSplit, MEDS["trainSplit"]) in graph
    assert (subj_uris[0], MEDS.assignedSplit, MEDS["tuningSplit"]) not in graph
    assert (subj_uris[1], MEDS.assignedSplit, MEDS["heldOutSplit"]) in graph
    assert (subj_uris[2], MEDS.assignedSplit, MEDS["tuningSplit"]) in graph

    split_name = "invalid_split_name"
    with raises(ValueError) as excinfo:
        invalid_split = pl.DataFrame([{"subject_id": 1, "split": split_name}])
        map_on_load(
            data=invalid_split.lazy(),
            entity="Split",
            map_fn=map_split_df,
            sink=sink,
            provenance=None,
            batch_size=100,
        )
        sink.close()

    assert f"The given split name '{split_name}' is not valid" in str(excinfo.value)
