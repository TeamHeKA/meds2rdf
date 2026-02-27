from pathlib import Path

import polars as pl
from pytest import raises
from rdflib import Graph, URIRef

from meds2rdf.mapping.split_mapper import map_split_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.utils.load_utils import load_and_parse_meds_table


def test_map_split_table_adds_subjectsplit_triples(tmp_path):
    graph = Graph()

    splits = pl.DataFrame(
        [
            {"subject_id": 1, "split": "train"},
            {"subject_id": 2, "split": "held_out"},
            {"subject_id": 3, "split": "tuning"},
        ]
    )

    path = Path(tmp_path / "split.parquet")
    splits.write_parquet(path)

    load_and_parse_meds_table(
        files_path=[path],
        entity="Split",
        map_fn=map_split_df,
        out_dir=tmp_path,
        storage=graph,
        provenance=None,
    )

    subj_uris = [
        URIRef(MEDS_INSTANCES["subject/1"]),
        URIRef(MEDS_INSTANCES["subject/2"]),
        URIRef(MEDS_INSTANCES["subject/3"]),
    ]

    # Basic assertions
    assert (subj_uris[0], MEDS.assignedSplit, MEDS["trainSplit"]) in graph
    assert (subj_uris[0], MEDS.assignedSplit, MEDS["tuningSplit"]) not in graph
    assert (subj_uris[1], MEDS.assignedSplit, MEDS["heldOutSplit"]) in graph
    assert (subj_uris[2], MEDS.assignedSplit, MEDS["tuningSplit"]) in graph

    split_name = "invalid_split_name"
    with raises(ValueError) as excinfo:
        invalid_split = pl.DataFrame([{"subject_id": 1, "split": split_name}])
        path = Path(tmp_path / "invalid_split.parquet")
        invalid_split.write_parquet(path)
        load_and_parse_meds_table(
            files_path=[path],
            entity="Split",
            map_fn=map_split_df,
            out_dir=tmp_path,
            storage=graph,
            provenance=None,
        )

    assert f"The given split name '{split_name}' is not valid" in str(excinfo.value)
