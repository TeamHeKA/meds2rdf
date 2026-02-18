from rdflib import RDF, Graph, Literal, URIRef

from meds2rdf.utils.load_utils import BATCH_SIZE
from ..namespace import MEDS
from ..utils.rdf_utils import to_subject_node, update_graph_lazy
import polars as pl

# Map split names to RDF predicates
_split_dict = {
    "train": MEDS.trainSplit,
    "tuning": MEDS.tuningSplit,
    "held_out": MEDS.heldOutSplit
}

# Keep track of splits that were already added to the graph
_seen_splits = set()

def map_split(
    row: tuple,
    col_idx: dict[str, int]
) -> tuple[URIRef, list[tuple]]:
    """
    Map a single Polars row (tuple) to a SubjectSplit RDF individual.
    Returns the URI of the created split.
    """
    triples = []
    subject_id = row[col_idx["subject_id"]]
    assigned_split = row[col_idx["split"]]

    if (split_uri := _split_dict.get(assigned_split)) is None:
        raise ValueError(f"The given split name '{assigned_split}' is not valid")
    
    # Link the subject to its split
    triples.append((to_subject_node(subject_id), MEDS.assignedSplit, split_uri))

    # Only create the split node once
    if assigned_split not in _seen_splits:
        triples.append((split_uri, RDF.type, MEDS.SubjectSplit))
        triples.append((split_uri, MEDS.splitName, Literal(assigned_split)))
        _seen_splits.add(assigned_split)

    return (split_uri, triples)


def map_split_table(g: Graph, data: pl.DataFrame) -> list[URIRef]:
    """
    Map a Polars DataFrame of SubjectSplitSchema rows to RDF triples.
    Returns the list of split URIs.
    """
    return update_graph_lazy(data, g, lambda r, ci, _: map_split(r, ci))