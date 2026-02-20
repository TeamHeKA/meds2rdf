from rdflib import RDF, Literal, URIRef

from ..namespace import MEDS
from ..utils.rdf_utils import to_subject_node

# Map split names to RDF predicates
_split_dict = {
    "train": MEDS.trainSplit,
    "tuning": MEDS.tuningSplit,
    "held_out": MEDS.heldOutSplit
}

def map_split(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> list[tuple[URIRef, URIRef, URIRef]]:
    """
    Map a single Polars row (tuple) to a SubjectSplit RDF individual.
    Returns the URI of the created split.
    """
    triples = []
    subject_id = row[col_idx["subject_id"]]
    assigned_split = row[col_idx["split"]]

    if (split_uri := _split_dict.get(assigned_split)) is None:
        raise ValueError(f"The given split name '{assigned_split}' is not valid")
    
    triples.append((to_subject_node(subject_id), MEDS.assignedSplit, split_uri))

    triples.append((split_uri, RDF.type, MEDS.SubjectSplit))
    triples.append((split_uri, MEDS.splitName, Literal(assigned_split)))

    return triples