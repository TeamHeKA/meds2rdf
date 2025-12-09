from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD
import uuid
from typing import Optional, Iterable
from ..namespace import MEDS, MEDS_INSTANCES, PROV
from ..utils.rdf_utils import *

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

def map_measurement(
    g: Graph,
    row: dict,
    dataset_uri: Optional[URIRef] = None,
    generate_code_node: bool = False
) -> URIRef:
    """
    Map a single row of a MEDS DataSchema into a Measurement RDF individual.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    row : dict
        Dictionary representing a single measurement (subject_id, time, code, numeric_value, text_value, site_id)
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link via prov:wasDerivedFrom
    generate_code_node : bool
        Whether to create a Code individual

    Returns
    -------
    URIRef
        URI of the created Measurement individual
    """
    # Create unique URI for the measurement
    measurement_uri = URIRef(base=MEDS_INSTANCES, value=f"measurement/{uuid.uuid4()}")
    g.add((measurement_uri, RDF.type, MEDS.Measurement))

    # ---------------------------
    # Subject
    # ---------------------------
    subject_id = try_access_mandatory_field_value(row=row, field="subject_id", entity="Measurement")
    subject_uri = to_subject_node(subject_id)
    g.add((measurement_uri, MEDS.hasSubject, subject_uri))
    g.add((subject_uri, RDF.type, MEDS.Subject))
    g.add((subject_uri, MEDS.subjectId, Literal(str(subject_id), datatype=XSD.string)))

    # ---------------------------
    # Code
    # ---------------------------
    code_str = try_access_mandatory_field_value(row=row, field="code", entity="Measurement")
    g.add((measurement_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    
    # Optionally create Code individual
    if generate_code_node: 
        code_uri = add_code(code_str=code_str, graph=g)
        g.add((measurement_uri, MEDS.hasCode, code_uri))

    # ---------------------------
    # Link to dataset metadata if provided
    # ---------------------------
    if dataset_uri:
        g.add((measurement_uri, PROV.wasDerivedFrom, dataset_uri))

    for column_name, (p, dtype) in _literals_dict.items():
        if_column_is_present(column_name, row, lambda v: g.add((measurement_uri, p, to_literal(v, dtype))))

    return measurement_uri


def map_data_table(
    g: Graph,
    data: Iterable[dict],
    dataset_uri: Optional[URIRef] = None,
    generate_code_node: bool = False
) -> list[URIRef]:
    """
    Map an iterable of MEDS DataSchema rows to RDF Measurement individuals.

    Parameters
    ----------
    g : Graph
        RDF graph to populate
    data : Iterable[dict]
        List of rows/dicts representing the MEDS DataSchema
    dataset_uri : Optional[URIRef]
        URI of the dataset metadata to link all measurements to
    generate_code_node : bool
        Whether to create a Code individual

    Returns
    -------
    list[URIRef]
        List of URIs of the created Measurement individuals
    """
    uris = []
    for row in data:
        measurement_uri = map_measurement(g, row, dataset_uri, generate_code_node)
        uris.append(measurement_uri)
    return uris
