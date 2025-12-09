from rdflib import Graph, URIRef
from rdflib.namespace import RDF, XSD
import uuid

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import if_column_is_present, to_literal

_literals_dict = {
    # Simple string or datetime fields
    "dataset_name": (MEDS.datasetName, XSD.string),
    "dataset_version": (MEDS.datasetVersion, XSD.string),
    "etl_version": (MEDS.etlVersion, XSD.string),
    "etl_notes": (MEDS.etlNotes, XSD.string),
    "meds_version": (MEDS.medsVersion, XSD.string),
    "protocol_notes": (MEDS.protocolNotes, XSD.string),
    "created_at": (MEDS.createdAt, XSD.dateTime),
    "etl_name": (MEDS.etlName, XSD.string),
    "license": (MEDS.license, XSD.string),
    "location_uri": (MEDS.locationUri, XSD.anyURI),
    "description_uri": (MEDS.descriptionUri, XSD.string),

    # List-like fields (may repeat triples)
    "site_id_columns": (MEDS.siteIdColumn, XSD.string),
    "subject_id_columns": (MEDS.subjectIdColumn, XSD.string),
    "table_names": (MEDS.tableName, XSD.string),
    "raw_source_id_columns": (MEDS.rawSourceIdColumn, XSD.string),
    "code_modifier_columns": (MEDS.codeModifierColumn, XSD.string),
    "additional_value_modality_columns": (MEDS.additionalValueModalityColumn, XSD.string),
    "other_extension_columns": (MEDS.otherExtensionColumn, XSD.string),
}

def map_dataset_metadata(g: Graph, shards: dict) -> URIRef:
    """
    Map a DatasetMetadataSchema JSON object into an RDF individual of type MEDS:DatasetMetadata.

    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph where triples will be added.
    shards : dict
        Dictionary following DatasetMetadataSchema (all fields optional).

    Returns
    -------
    URIRef
        The URI of the created DatasetMetadata individual.
    """
    
    dataset_uri = URIRef(base=MEDS_INSTANCES, value=f"dataset_metadata/{uuid.uuid4()}")
    g.add((dataset_uri, RDF.type, MEDS.DatasetMetadata))

    for column_name, (p, dtype) in _literals_dict.items():
        if_column_is_present(column_name, shards, lambda v: g.add((dataset_uri, p, to_literal(v, dtype))))

    return dataset_uri