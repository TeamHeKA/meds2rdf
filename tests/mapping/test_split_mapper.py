from pytest import raises
from rdflib import Graph, URIRef
from meds2rdf.mapping.split_mapper import map_split_table
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
import polars as pl

def test_map_split_table_adds_subjectsplit_triples():
    graph = Graph()
    
    splits = pl.DataFrame([
        {"subject_id": 1, "split": "train"},
        {"subject_id": 2, "split": "held_out"},
        {"subject_id": 3, "split": "tuning"}
    ])
    
    map_split_table(graph, splits)

    subj_uris = [
        URIRef(MEDS_INSTANCES["subject/1"]), 
        URIRef(MEDS_INSTANCES["subject/2"]), 
        URIRef(MEDS_INSTANCES["subject/3"])
    ]
    
    # Basic assertions
    assert (subj_uris[0], MEDS.assignedSplit, MEDS["trainSplit"]) in graph
    assert not (subj_uris[0], MEDS.assignedSplit, MEDS["tuningSplit"]) in graph
    assert (subj_uris[1], MEDS.assignedSplit, MEDS["heldOutSplit"]) in graph
    assert (subj_uris[2], MEDS.assignedSplit, MEDS["tuningSplit"]) in graph

    split_name = "invalid_split_name"
    with raises(ValueError) as excinfo:
        map_split_table(graph, data = pl.DataFrame([{"subject_id": 1, "split": split_name}]))

    assert f"The given split name '{split_name}' is not valid" in str(excinfo.value)

