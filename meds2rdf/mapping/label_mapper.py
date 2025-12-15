import uuid
from rdflib import Graph, URIRef, RDF, XSD, PROV
from typing import Iterable, Optional
from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import *

_literals_dict = {
    "description": (MEDS.codeDescription, XSD.string),
    "prediction_time": (MEDS.predictionTime, XSD.dateTime),
    "boolean_value": (MEDS.booleanValue, XSD.boolean),
    "integer_value": (MEDS.integerValue, XSD.int),
    "float_value": (MEDS.floatValue, XSD.double),
    "categorical_value": (MEDS.categoricalValue, XSD.string),
}

def map_label(g: Graph, row: dict, dataset_uri: Optional[URIRef] = None) -> URIRef:
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

    # Create unique URI for the label_sample
    label_sample_uri = URIRef(MEDS_INSTANCES[f"label_sample/{uuid.uuid4()}"])
    g.add((label_sample_uri, RDF.type, MEDS.LabelSample))

    subject_id = try_access_mandatory_field_value(row=row, field="subject_id", entity="Label")
    g.add((label_sample_uri, MEDS.hasSubject, to_subject_node(subject_id)))

    for column_name, (p, dtype) in _literals_dict.items():
        if_column_is_present(column_name, row, lambda v: g.add((label_sample_uri, p, to_literal(v, dtype))))

    if dataset_uri:
        g.add((label_sample_uri, PROV.wasDerivedFrom, dataset_uri))

    return label_sample_uri


def map_label_table(
    g: Graph,
    data: Iterable[dict],
    dataset_uri: Optional[URIRef] = None,
) -> list[URIRef]:
    """
    Map an iterable of MEDS LabelSchema rows to RDF LabelSample individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        List of rows/dicts representing the MEDS LabelSchema
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link via prov:wasDerivedFrom

    Returns
    -------
    list[URIRef]
        List of URIs of the created LabelSample individuals
    """
    uris = []
    for row in data:
        label_sample_uri = map_label(g, row, dataset_uri)
        uris.append(label_sample_uri)
    return uris
