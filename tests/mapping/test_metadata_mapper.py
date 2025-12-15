from rdflib import Graph, Literal, XSD, URIRef, RDF, RDFS, DCAT, PROV, DCTERMS as DCT
from meds2rdf.mapping.metadata_mapper import map_dataset_metadata
from meds2rdf.namespace import MEDS, MEDS_INSTANCES

def test_map_dataset_metadata_adds_triples():
    graph = Graph()

    metadata = {
        "dataset_name": "Demo Dataset",
        "dataset_version": "1.0",
        "meds_version": "0.3.3",
        "created_at": "2025-01-01T00:00:00",
        "license": "https://opensource.org/licenses/MIT",
        "location_uri": "https://example.com/dataset.zip",
        "description_uri": "https://example.com/dataset_description.html",
        "etl_name": "demo_etl",
        "etl_version": "0.1",
        "etl_notes": "Initial conversion from raw CSV.",
        "protocol_notes": "Applied basic filtering.",
        "site_id_columns": ["site_id_1", "site_id_2"],
        "subject_id_columns": ["subject_id"],
        "raw_source_id_columns": ["source_id_1"],
        "code_modifier_columns": ["modifier_1", "modifier_2"],
        "additional_value_modality_columns": ["modality_1"],
        "other_extension_columns": ["extra_column"]
    }

    dataset_uri = map_dataset_metadata(graph, metadata)

    graph.print()

    # Type assertions
    assert (dataset_uri, RDF.type, MEDS.DatasetMetadata) in graph

    # Literal assertions
    assert (dataset_uri, MEDS.medsVersion, Literal("0.3.3", datatype=XSD.string)) in graph
    assert (dataset_uri, DCT.title, Literal("Demo Dataset", datatype=XSD.string)) in graph
    #assert (dataset_uri, DCT.hasVersion, Literal("1.0", datatype=XSD.string)) in graph
    assert (dataset_uri, DCT.created,Literal("2025-01-01T00:00:00", datatype=XSD.dateTime)) in graph
    #assert (dataset_uri, DCT.license, URIRef("https://opensource.org/licenses/MIT")) in graph

    # Check repeated column literals
    for site_id in metadata["site_id_columns"]:
        assert (dataset_uri, MEDS.siteIdColumn, Literal(site_id, datatype=XSD.string)) in graph

    # Check distribution node for location_uri
    dist_triples = list(graph.triples((None, DCAT.downloadURL, URIRef(metadata["location_uri"]))))
    assert len(dist_triples) == 1
    dist_uri = dist_triples[0][0]
    # Distribution should be linked from dataset
    assert (dataset_uri, DCAT.distribution, dist_uri) in graph
    # Optional description_uri
    assert (dist_uri, DCAT.accessURL, URIRef(metadata["description_uri"])) in graph

    # Check prov:Activity for ETL metadata
    activity_triples = list(graph.triples((dataset_uri, PROV.wasGeneratedBy, None)))
    assert len(activity_triples) == 1
    activity_uri = activity_triples[0][2]
    assert (activity_uri, RDF.type, PROV.Activity) in graph
    assert (activity_uri, RDFS.label, Literal(metadata["etl_name"], datatype=XSD.string)) in graph
    # assert (activity_uri, DCAT.hasVersion, Literal(metadata["etl_version"], datatype=XSD.string)) in graph
    # notes concatenated
    combined_notes = metadata["etl_notes"] + "\n\n" + metadata["protocol_notes"]
    assert (activity_uri, RDFS.comment, Literal(combined_notes, datatype=XSD.string)) in graph

