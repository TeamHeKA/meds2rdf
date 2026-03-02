import uuid
from collections.abc import Generator

import polars as pl
from rdflib import Literal, URIRef
from rdflib.namespace import DCAT, PROV, RDF, RDFS, XSD
from rdflib.namespace import DCTERMS as DCT

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
    df: pl.DataFrame,
    offset: int,
    dataset_uri: URIRef,
) -> Generator[tuple[URIRef, URIRef, URIRef | Literal], None, None]:
    """
    Yield RDF triples for a DatasetMetadataSchema dict.

    Fully streaming, no graph mutation; returns triples like
    map_event_df/map_label_df for consistency.
    """
    _dict = df.to_dict()

    # ---- Types ----
    yield (dataset_uri, RDF.type, MEDS.DatasetMetadata)
    yield (dataset_uri, RDF.type, DCAT.Dataset)

    # ---- Simple literal fields ----
    for field, (prop, dtype) in _literals_dict.items():
        if field in _dict and _dict[field][0] is not None:
            yield (dataset_uri, prop, to_literal(_dict[field][0], dtype))

    # ---- Repeated literal column lists ----
    for field, (prop, dtype) in _column_list_dict.items():
        if field in _dict and _dict[field].len() > 0:
            values = _dict[field][0].to_list()
            for v in values:
                yield (dataset_uri, prop, to_literal(v, dtype))

    # ---- Dataset version ----
    if "dataset_version" in _dict and _dict["dataset_version"][0] is not None:
        version_uri = URIRef(f"{dataset_uri}_{_dict['dataset_version'][0]}")
        yield (dataset_uri, DCT.hasVersion, version_uri)

    # ---- License ----
    if "license" in _dict and _dict["license"][0] is not None:
        license_uri = URIRef(MEDS_INSTANCES[f"dataset_license/{uuid.uuid4()}"])
        yield (license_uri, RDF.type, DCT.LicenseDocument)
        yield (license_uri, RDFS.label, to_literal(_dict["license"][0], XSD.string))
        yield (dataset_uri, DCT.license, license_uri)

    # ---- Distribution ----
    if (location := _dict.get("location_uri")) is not None:
        dist_uri = URIRef(MEDS_INSTANCES[f"distribution/{uuid.uuid4()}"])
        yield (dist_uri, RDF.type, DCAT.Distribution)
        try:
            yield (dist_uri, DCAT.downloadURL, URIRef(location[0]))
        except Exception:
            yield (dist_uri, DCAT.downloadURL, to_literal(location[0], XSD.anyURI))
        if (description := _dict.get("description_uri")) is not None:
            try:
                yield (dist_uri, DCAT.accessURL, URIRef(description[0]))
            except Exception:
                yield (dist_uri, DCAT.accessURL, to_literal(description[0], XSD.anyURI))
        yield (dataset_uri, DCAT.distribution, dist_uri)

    # ---- ETL activity ----
    activity_uri = URIRef(MEDS_INSTANCES[f"etl/{uuid.uuid4()}"])
    yield (activity_uri, RDF.type, PROV.Activity)
    yield (dataset_uri, PROV.wasGeneratedBy, activity_uri)

    if (etl_name := _dict.get("etl_name")) is not None:
        yield (activity_uri, RDFS.label, to_literal(etl_name[0], XSD.string))
    if (etl_version := _dict.get("etl_version")) is not None:
        yield (activity_uri, DCT.hasVersion, URIRef(f"{activity_uri}_{etl_version[0]}"))

    notes = ""
    if (etl_notes := _dict.get("etl_notes")) is not None:
        notes = etl_notes[0]
    if (protocol_notes := _dict.get("protocol_notes")) is not None:
        notes = "\n\n".join([notes, protocol_notes[0]])
    if notes != "":
        yield (activity_uri, RDFS.comment, to_literal(notes, XSD.string))
