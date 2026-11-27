"""Regression tests for bugs found in v2.0.0."""

import gzip
from collections import Counter

import polars as pl
import pytest
from rdflib import RDF, XSD, Graph, Literal, URIRef

from meds2rdf import Config, MedsRDFConverter, MEDSSchema, NTriplesSink, SemanticMode
from meds2rdf.mapping.code_mapper import map_code_df
from meds2rdf.mapping.event_mapper import map_event_df
from meds2rdf.mapping.label_mapper import map_label_df
from meds2rdf.mapping.metadata_mapper import map_dataset_metadata_df
from meds2rdf.namespace import MEDS, MEDS_INSTANCES
from meds2rdf.utils.rdf_utils import curie_to_uri

TRICKY = [
    "Normal <3 Seconds",
    "Abnormal >3 Seconds",
    'say "hi"',
    "a\\b",
    "x  y",
    "[ref]",
    "__x__",
    "{a|b}",
    "line1\nline2",
    "tab\there",
    "trailing ",
]


def _events(codes, **cols):
    return pl.DataFrame({"subject_id": [1] * len(codes), "code": codes, **cols})


@pytest.mark.parametrize("mode", list(SemanticMode))
def test_event_triples_are_not_duplicated(mode):
    triples = list(map_event_df(_events(["A//1", "A//2", "A//1", "A//1"]), 0, mode=mode))
    dup = [t for t, n in Counter(triples).items() if n > 1]
    assert dup == []
    ev = URIRef(MEDS_INSTANCES["event/1_0"])
    assert (ev, MEDS.hasSubject, URIRef(MEDS_INSTANCES["subject/1"])) in triples


def test_text_and_code_literals_are_preserved(tmp_path):
    df = _events(TRICKY, text_value=TRICKY)
    sink = NTriplesSink(tmp_path, gzip_mode=False)
    sink.add_many(map_event_df(df, 0))
    sink.close()
    g = Graph().parse(tmp_path / "part-00000.nt", format="nt")  # must be valid N-Triples
    texts = {str(o) for o in g.objects(None, MEDS.textValue)}
    codes = {str(o) for s, o in g.subject_objects(MEDS.codeString) if "/event/" in str(s)}
    assert texts == set(TRICKY)
    assert codes == set(TRICKY)


def test_code_metadata_attaches_to_event_code_node():
    code = 'LAB  1"x" (mg) '
    ev_code = next(o for _, p, o in map_event_df(_events([code]), 0) if p == MEDS.hasCode)
    triples = list(map_code_df(pl.DataFrame({"code": [code], "description": ['desc <1> "q"']}), 0))
    assert (ev_code, RDF.type, MEDS.Code) in triples
    assert (ev_code, MEDS.codeString, Literal(code, datatype=XSD.string)) in triples
    assert (ev_code, MEDS.codeDescription, Literal('desc <1> "q"', datatype=XSD.string)) in triples


def test_parent_code_triples_emitted_once_per_batch():
    df = pl.DataFrame({"code": ["A", "B"], "parent_codes": [["LOINC/1-2"], ["LOINC/1-2"]]})
    triples = list(map_code_df(df, 0))
    assert [n for n in Counter(triples).values() if n > 1] == []
    assert sum(1 for _, p, _ in triples if p == MEDS.parentCode) == 2


def test_external_code_iri_is_valid():
    uri = curie_to_uri("SNOMED/123 456<x>")
    assert " " not in uri and "<" not in uri
    assert uri == URIRef("http://purl.bioontology.org/ontology/SNOMED/123%20456%3Cx%3E")
    assert curie_to_uri("LOINC/2347-3") == URIRef("http://purl.bioontology.org/ontology/LNC/2347-3")


def test_label_string_literals_are_preserved():
    df = pl.DataFrame({"subject_id": [1], "categorical_value": ["<5 days"]})
    assert (
        URIRef(MEDS_INSTANCES["label/1_0"]),
        MEDS.categoricalValue,
        Literal("<5 days", datatype=XSD.string),
    ) in list(map_label_df(df, 0))


def test_metadata_nulls_do_not_become_literals():
    uri = URIRef(MEDS_INSTANCES["dataset_metadata/x"])
    df = pl.DataFrame(
        {
            "dataset_name": ["d"],
            "etl_name": [None],
            "etl_version": [None],
            "location_uri": [None],
            "etl_notes": [None],
            "protocol_notes": ["p"],
            "site_id_columns": [None],
        },
        schema_overrides={"site_id_columns": pl.List(pl.Utf8)},
    )
    triples = list(map_dataset_metadata_df(df, 0, uri))
    assert all(str(o) != "None" for _, _, o in triples)
    assert any(str(o) == "p" for _, _, o in triples)  # protocol notes without a leading "\n\n"


def _write_meds(root):
    (root / "data").mkdir(parents=True)
    (root / "metadata").mkdir()
    (root / "labels" / "task_a").mkdir(parents=True)
    (root / "labels" / "task_b").mkdir(parents=True)
    pl.DataFrame({"subject_id": [1, 2], "code": ["A", "B"]}).write_parquet(
        root / "data" / "0.parquet"
    )
    for t, v in [("task_a", True), ("task_b", False)]:
        pl.DataFrame({"subject_id": [1], "boolean_value": [v]}).write_parquet(
            root / "labels" / t / "0.parquet"
        )


def test_converter_exports_labels_from_task_directories(tmp_path):
    _write_meds(tmp_path / "meds")
    MedsRDFConverter(tmp_path / "meds").convert(
        NTriplesSink(tmp_path / "out", gzip_mode=False), Config(schemas={MEDSSchema.LABELS})
    )
    g = Graph().parse(tmp_path / "out" / "part-00000.nt", format="nt")
    assert len(set(g.subjects(RDF.type, MEDS.LabelSample))) == 2


def test_nt_sink_rotation_leaves_no_empty_file(tmp_path):
    sink = NTriplesSink(tmp_path, gzip_mode=True)
    sink.max_triples_per_file = 2
    for i in range(4):
        sink.add(URIRef(f"http://a/{i}"), URIRef("http://p"), URIRef("http://o"))
    sink.close()
    parts = sorted(tmp_path.iterdir())
    assert [p.name for p in parts] == ["part-00000.nt.gz", "part-00001.nt.gz"]
    assert all(len(gzip.open(p, "rt").read().splitlines()) == 2 for p in parts)
