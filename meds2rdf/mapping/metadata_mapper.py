from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS as DCT, PROV, DCAT
import uuid

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import if_column_is_present, to_literal

# Mapping for simple literal properties (dataset-level)
# NOTE: ETL fields are handled separately (as a prov:Activity)
_literals_dict = {
    "dataset_name": (DCT.title, XSD.string),
    "meds_version": (MEDS.medsVersion, XSD.string),
    "created_at": (DCT.created, XSD.dateTime),
    # keep description_uri/location handled via distribution (see below)
}

# MEDS-specific repeated-literal properties (one triple per column)
_column_list_dict = {
    "site_id_columns": (MEDS.siteIdColumn, XSD.string),
    "subject_id_columns": (MEDS.subjectIdColumn, XSD.string),
    "raw_source_id_columns": (MEDS.rawSourceIdColumn, XSD.string),
    "code_modifier_columns": (MEDS.codeModifierColumn, XSD.string),
    "additional_value_modality_columns": (MEDS.additionalValueModalityColumn, XSD.string),
    "other_extension_columns": (MEDS.otherExtensionColumn, XSD.string),
}


def _add_distribution_for_dataset(g: Graph, dataset_uri: URIRef, shards: dict) -> URIRef | None:
    """
    If location_uri is present in shards, create a dcat:Distribution node,
    attach dcat:downloadURL (and optional dcat:accessURL), and link it to the dataset.
    Returns the distribution URI or None if not created.
    """
    location = shards.get("location_uri")
    description = shards.get("description_uri")

    if not location:
        return None

    dist_uri = URIRef(MEDS_INSTANCES[f"distribution/{uuid.uuid4()}"])
    g.add((dist_uri, RDF.type, DCAT.Distribution))
    # downloadURL should be an IRI (URIRef)
    try:
        g.add((dist_uri, DCAT.downloadURL, URIRef(location)))
    except Exception:
        # fallback to literal if the helper expects that (safe fallback)
        g.add((dist_uri, DCAT.downloadURL, to_literal(location, XSD.anyURI)))

    if description:
        try:
            g.add((dist_uri, DCAT.accessURL, URIRef(description)))
        except Exception:
            g.add((dist_uri, DCAT.accessURL, to_literal(description, XSD.anyURI)))

    # link dataset -> distribution
    g.add((dataset_uri, DCAT.distribution, dist_uri))
    return dist_uri


def _add_etl_activity_if_present(g: Graph, dataset_uri: URIRef, shards: dict) -> URIRef | None:
    """
    If any ETL-related fields are present (etl_name, etl_version, etl_notes, protocol_notes),
    create a prov:Activity node and attach relevant literals using standard properties:
      - rdfs:label for etl_name
      - dct:hasVersion for etl_version
      - rdfs:comment for etl_notes / protocol_notes (concatenated if both)
    Link the dataset via prov:wasGeneratedBy -> activity.
    Returns the activity URI or None if nothing was created.
    """
    etl_name = shards.get("etl_name")
    etl_version = shards.get("etl_version")
    etl_notes = shards.get("etl_notes")
    protocol_notes = shards.get("protocol_notes")

    if not any((etl_name, etl_version, etl_notes, protocol_notes)):
        return None

    activity_uri = URIRef(MEDS_INSTANCES[f"etl/{uuid.uuid4()}"])
    g.add((activity_uri, RDF.type, PROV.Activity))
    g.add((dataset_uri, PROV.wasGeneratedBy, activity_uri))

    if_column_is_present("etl_name", shards, lambda v:  g.add((activity_uri, RDFS.label, to_literal(v, XSD.string))))
    if_column_is_present("etl_version", shards, lambda v: _add_version_node(g, activity_uri, version=v))

    # combine notes if both are present
    notes_parts = []
    if etl_notes:
        notes_parts.append(str(etl_notes))
    if protocol_notes:
        notes_parts.append(str(protocol_notes))
    if notes_parts:
        combined = "\n\n".join(notes_parts)
        g.add((activity_uri, RDFS.comment, to_literal(combined, XSD.string)))

    return activity_uri


def _add_version_node(g: Graph, resource_uri: URIRef, version: str):
    return g.add((resource_uri, DCT.hasVersion, URIRef(f"{resource_uri}_{version}")))

def _add_license_node(g: Graph, dataset_uri: URIRef, license_text: str):
    license_uri = MEDS_INSTANCES[f"dataset_license/{uuid.uuid4()}"]
    g.add((license_uri, RDF.type, DCT.LicenseDocument))
    g.add((license_uri, RDFS.label, to_literal(license_text, XSD.string)))
    g.add((dataset_uri, DCT.license, license_uri))
    return g

def map_dataset_metadata(g: Graph, shards: dict) -> URIRef:
    """
    Map a DatasetMetadataSchema JSON-like dict into an RDF individual of type MEDS:DatasetMetadata
    (and also typed as dcat:Dataset for catalog compatibility).

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
    dataset_uri = URIRef(MEDS_INSTANCES[f"dataset_metadata/{uuid.uuid4()}"])
    # Type as MEDS DatasetMetadata and DCAT Dataset (for interoperability)
    g.add((dataset_uri, RDF.type, MEDS.DatasetMetadata))

    # simple literal mappings
    for field, (prop, dtype) in _literals_dict.items():
        if_column_is_present(field, shards, lambda v: g.add((dataset_uri, prop, to_literal(v, dtype))))

    # repeated-literal MEDS column lists
    for field, (prop, dtype) in _column_list_dict.items():
        if_column_is_present(field, shards, lambda v: g.add((dataset_uri, prop, to_literal(v, dtype))))

    if_column_is_present("dataset_version", shards, lambda v: _add_version_node(g, dataset_uri, version=v))
    if_column_is_present("license", shards, lambda v: _add_license_node(g, dataset_uri, license_text=v))

    # Distribution (location_uri + optional description_uri)
    _add_distribution_for_dataset(g, dataset_uri, shards)

    # ETL provenance recorded as a prov:Activity (if any ETL info provided)
    _add_etl_activity_if_present(g, dataset_uri, shards)

    return dataset_uri
