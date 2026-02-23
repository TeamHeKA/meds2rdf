from pathlib import Path

from meds2rdf.mapping.code_mapper import map_code_df
from meds2rdf.utils.load_utils import load_and_parse_meds_table2
from rdflib import Graph, URIRef, Literal, XSD
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.utils.rdf_utils import curie_to_uri
import polars as pl

def test_map_code_table_adds_code_triples(tmp_path):
    graph = Graph()
    
    codes = pl.DataFrame([
        {"code": "CODE1//A", "description": "Test code", "parent_codes": ["nocode/111"]},
        {"code": "CODE2", "description": "Child code", "parent_codes": ["ATC:ABC"]},
        {"code": "CODE3", "description": "Test code", "parent_codes": ["LOINC/1234", None, ""]},
    ])

    path = Path(tmp_path / "codes.parquet")
    codes.write_parquet(path)

    # Pass list[Path] as expected
    load_and_parse_meds_table2(
        files_path=[path],
        entity="Code",
        map=map_code_df,
        storage=graph,
        provenance=None
    )

    graph.print()

    # --- Assertions ---
    code1_uri = URIRef(MEDS_INSTANCES["code/CODE1_A"])
    code2_uri = URIRef(MEDS_INSTANCES["code/CODE2"])
    codec_uri = URIRef(MEDS_INSTANCES["code/CODE3"])

    code3_uri = curie_to_uri(codes[1, "parent_codes"][0])
    code4_uri = curie_to_uri(codes[0, "parent_codes"][0])
    code5_uri = curie_to_uri(codes[2, "parent_codes"][0])


    #assert (code1_uri, MEDS.codeString, Literal("CODE1//A", datatype=XSD.string)) in graph
    assert (code1_uri, MEDS.codeDescription, Literal("Test code", datatype=XSD.string)) in graph
    assert (code2_uri, MEDS.parentCode, code3_uri) in graph
    assert (code1_uri, MEDS.parentCode, code4_uri) in graph
    assert (codec_uri, MEDS.parentCode, code5_uri) in graph

    assert sum(1 for _ in graph.triples((codec_uri, MEDS.parentCode, None))) == 1
