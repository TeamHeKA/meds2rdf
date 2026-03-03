import polars as pl
from rdflib import XSD, Graph, Literal, URIRef

from meds2rdf.mapping.code_mapper import map_code_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.utils import map_on_load
from meds2rdf.utils.rdf_utils import curie_to_uri


def test_map_code_table_adds_code_triples(tmp_path):
    graph = Graph()

    codes = pl.DataFrame(
        [
            {"code": "CODE1//A", "description": "Test code", "parent_codes": ["nocode/111"]},
            {"code": "CODE2", "description": "Child code", "parent_codes": ["ATC:ABC"]},
            {"code": "CODE3", "description": "Test code", "parent_codes": ["LOINC/1234", None, ""]},
        ]
    )

    # path = Path(tmp_path / "codes.parquet")
    sink = GraphSink(graph)
    # codes.write_parquet(path)

    # Pass list[Path] as expected
    map_on_load(
        data=codes.lazy(),
        entity="Code",
        map_fn=map_code_df,
        sink=sink,
        batch_size=100,
        provenance=None,
    )

    graph.print()

    sink.close()

    # --- Assertions ---
    code1_uri = URIRef(MEDS_INSTANCES["code/CODE1_A"])
    code2_uri = URIRef(MEDS_INSTANCES["code/CODE2"])
    codec_uri = URIRef(MEDS_INSTANCES["code/CODE3"])

    code3_uri = curie_to_uri(codes[1, "parent_codes"][0])
    code4_uri = curie_to_uri(codes[0, "parent_codes"][0])
    code5_uri = curie_to_uri(codes[2, "parent_codes"][0])

    # assert (code1_uri, MEDS.codeString, Literal("CODE1//A", datatype=XSD.string)) in graph
    assert (code1_uri, MEDS.codeDescription, Literal("Test code", datatype=XSD.string)) in graph
    assert (code2_uri, MEDS.parentCode, code3_uri) in graph
    assert (code1_uri, MEDS.parentCode, code4_uri) in graph
    assert (codec_uri, MEDS.parentCode, code5_uri) in graph

    assert sum(1 for _ in graph.triples((codec_uri, MEDS.parentCode, None))) == 1
