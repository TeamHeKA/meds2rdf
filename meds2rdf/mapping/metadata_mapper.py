from typing import Generator

from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS as DCT, PROV, DCAT
import uuid

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import to_literal

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

def map_dataset_metadata_df(
    shards: dict,
    dataset_uri: URIRef,
) -> Generator[tuple[URIRef, URIRef, URIRef | Literal], None, None]:
    """
    Yield RDF triples for a DatasetMetadataSchema dict.

    Fully streaming, no graph mutation; returns triples like
    map_event_df/map_label_df for consistency.
    """
    # ---- Types ----
    yield (dataset_uri, RDF.type, MEDS.DatasetMetadata)
    yield (dataset_uri, RDF.type, DCAT.Dataset)

    # ---- Simple literal fields ----
    for field, (prop, dtype) in _literals_dict.items():
        if field in shards and shards[field] is not None:
            yield (dataset_uri, prop, to_literal(shards[field], dtype))

    # ---- Repeated literal column lists ----
    for field, (prop, dtype) in _column_list_dict.items():
        if field in shards and shards[field]:
            values = shards[field]
            if not isinstance(values, (list, tuple)):
                values = [values]
            for v in values:
                yield (dataset_uri, prop, to_literal(v, dtype))

    # ---- Dataset version ----
    if "dataset_version" in shards and shards["dataset_version"] is not None:
        version_uri = URIRef(f"{dataset_uri}_{shards['dataset_version']}")
        yield (dataset_uri, DCT.hasVersion, version_uri)

    # ---- License ----
    if "license" in shards and shards["license"] is not None:
        license_uri = URIRef(MEDS_INSTANCES[f"dataset_license/{uuid.uuid4()}"])
        yield (license_uri, RDF.type, DCT.LicenseDocument)
        yield (license_uri, RDFS.label, to_literal(shards["license"], XSD.string))
        yield (dataset_uri, DCT.license, license_uri)

    # ---- Distribution ----
    location = shards.get("location_uri")
    description = shards.get("description_uri")
    if location:
        dist_uri = URIRef(MEDS_INSTANCES[f"distribution/{uuid.uuid4()}"])
        yield (dist_uri, RDF.type, DCAT.Distribution)
        try:
            yield (dist_uri, DCAT.downloadURL, URIRef(location))
        except Exception:
            yield (dist_uri, DCAT.downloadURL, to_literal(location, XSD.anyURI))
        if description:
            try:
                yield (dist_uri, DCAT.accessURL, URIRef(description))
            except Exception:
                yield (dist_uri, DCAT.accessURL, to_literal(description, XSD.anyURI))
        yield (dataset_uri, DCAT.distribution, dist_uri)

    # ---- ETL activity ----
    etl_name = shards.get("etl_name")
    etl_version = shards.get("etl_version")
    etl_notes = shards.get("etl_notes")
    protocol_notes = shards.get("protocol_notes")
    if any((etl_name, etl_version, etl_notes, protocol_notes)):
        activity_uri = URIRef(MEDS_INSTANCES[f"etl/{uuid.uuid4()}"])
        yield (activity_uri, RDF.type, PROV.Activity)
        yield (dataset_uri, PROV.wasGeneratedBy, activity_uri)
        if etl_name:
            yield (activity_uri, RDFS.label, to_literal(etl_name, XSD.string))
        if etl_version:
            version_uri = URIRef(f"{activity_uri}_{etl_version}")
            yield (activity_uri, DCT.hasVersion, version_uri)
        notes = "\n\n".join([str(n) for n in (etl_notes, protocol_notes) if n])
        if notes:
            yield (activity_uri, RDFS.comment, to_literal(notes, XSD.string))
