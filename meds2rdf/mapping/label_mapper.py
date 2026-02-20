from rdflib import URIRef, RDF, XSD, PROV
from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import *

_literals_dict = {
    "description": (MEDS.codeDescription, XSD.string),
    "prediction_time": (MEDS.predictionTime, XSD.dateTime),
    "boolean_value": (MEDS.booleanValue, XSD.boolean),
    "integer_value": (MEDS.integerValue, XSD.integer),
    "float_value": (MEDS.floatValue, XSD.double),
    "categorical_value": (MEDS.categoricalValue, XSD.string),
}

def map_label(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> list[tuple[URIRef, URIRef, URIRef]]:
    """
    Map a single row of a MEDS LabelSchema into a LabelSample RDF individual.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    row : dict
        Dictionary representing a single label
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link via prov:wasDerivedFrom

    Returns
    -------
    URIRef
        URI of the created LabelSample individual
    """
    triples = []

    subject_id = row[col_idx["subject_id"]]
    label_sample_uri = URIRef(MEDS_INSTANCES[f"label/{subject_id}_{row_index}"])
    triples.append((label_sample_uri, RDF.type, MEDS.LabelSample))
    triples.append((label_sample_uri, MEDS.hasSubject, to_subject_node(subject_id)))

    for column_name, (p, dtype) in _literals_dict.items():
        if col_idx.get(column_name) is not None:
            if_exist(
                value=row[col_idx[column_name]], 
                run=lambda v: triples.append((label_sample_uri, p, to_literal(v, dtype)))
            )

    if dataset_uri:
        triples.append((label_sample_uri, PROV.wasDerivedFrom, dataset_uri))

    return triples