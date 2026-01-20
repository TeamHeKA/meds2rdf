from rdflib import Graph, URIRef, Literal, XSD
from meds2rdf.mapping.code_mapper import map_code_table
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.utils.rdf_utils import curie_to_uri

def test_map_code_table_adds_code_triples():
    graph = Graph()
    
    codes = [
        {"code": "CODE1", "description": "Test code", "parent_codes": [":"]},
        {"code": "CODE2", "description": "Child code", "parent_codes": ["ATC:ABC"]},
        {"code": "CODE3", "description": "Test code", "parent_codes": ["LOINC/1234", None, ""]},
    ]

    map_code_table(graph, codes, dataset_uri=None)

    code1_uri = URIRef(MEDS_INSTANCES["code/CODE1"])
    code2_uri = URIRef(MEDS_INSTANCES["code/CODE2"])
    codec_uri = URIRef(MEDS_INSTANCES["code/CODE3"])

    code3_uri = curie_to_uri(codes[1]["parent_codes"][0])
    code4_uri = curie_to_uri(codes[0]["parent_codes"][0])
    code5_uri = curie_to_uri(codes[2]["parent_codes"][0])

    assert (code1_uri, MEDS.codeString, Literal("CODE1", datatype=XSD.string)) in graph
    assert (code1_uri, MEDS.codeDescription, Literal("Test code", datatype=XSD.string)) in graph
    assert (code2_uri, MEDS.parentCode, code3_uri) in graph
    assert (code1_uri, MEDS.parentCode, code4_uri) in graph
    assert (codec_uri, MEDS.parentCode, code5_uri) in graph

    assert sum(1 for _ in graph.triples((codec_uri, MEDS.parentCode, None))) == 1

