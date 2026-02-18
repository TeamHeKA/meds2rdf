from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from rdflib import Literal, RDF, URIRef, Graph, PROV
from rdflib.namespace import XSD
from datetime import datetime
from typing import Optional, Callable, Iterable
import re

from meds2rdf.utils.load_utils import BATCH_SIZE
from ..namespace import MEDS, MEDS_INSTANCES, PREFIX_MAP_BIOPORTAL
import polars as pl

from pyshacl import validate

def run_shacl_validation(graph: Graph, shacl_file: str | Path):
    conforms, results_graph, results_text = validate(
        data_graph=graph,
        shacl_graph=str(shacl_file),
        inference='rdfs',
        abort_on_first=False,
        debug=False
    )

    if not conforms:
        raise ValueError(f"SHACL validation failed. {results_text}\n{results_graph}")

    return conforms

def to_literal(value, dtype):
    if isinstance(value, datetime):
        return Literal(value.isoformat(), datatype=XSD.dateTime)
    return Literal(str(value), datatype=dtype)

def try_access_mandatory_field_value(row, field, entity):
    val = row.get(field)
    if val is None:
        raise ValueError(f"{entity} must have field '{field}'")
    return val

def if_column_is_present(column_name, source, callback: Callable[[str], Any]):
    value = source.get(column_name)
    if value is None:
        return
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for v in value:
            callback(v)
    else:
        callback(str(value))


def if_exist(value: Any, run: Callable[[str], Any]):
    if value is None:
        return
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for v in value:
            run(v)
    else:
        run(str(value))

NT_IRI_REGEX = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+.-]*:[^\s<>\"{}|^`\\]+$"
)
    
SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")

def is_valid_nt_iri(iri: str) -> bool:
    return bool(NT_IRI_REGEX.match(iri))

def add_code(code_str: str, graph: Graph, dataset_uri: Optional[URIRef] = None, external = False) -> URIRef:
    if external: 
        code_uri = curie_to_uri(code_str)
    else:
        code_uri = URIRef(MEDS_INSTANCES[f"code/{SAFE_CHARS.sub("_", code_str.replace("//", "_"))}"])

    graph.add((code_uri, RDF.type, MEDS.Code))
    graph.add((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    if dataset_uri:
        graph.add((code_uri, PROV.wasDerivedFrom, dataset_uri))
        
    return code_uri


def generate_code(code_str: str, dataset_uri: Optional[URIRef] = None, external = False) -> tuple[URIRef, list]:
    triples = []
    if external: 
        code_uri = curie_to_uri(code_str)
    else:
        code_uri = URIRef(MEDS_INSTANCES[f"code/{SAFE_CHARS.sub("_", code_str.replace("//", "_"))}"])

    triples.append((code_uri, RDF.type, MEDS.Code))
    triples.append((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    if dataset_uri:
        triples.append((code_uri, PROV.wasDerivedFrom, dataset_uri))
        
    return (code_uri, triples)

def node_exist(graph: Graph, node: URIRef) -> bool:
    return (node, None, None) in graph

def to_subject_node(subject_id: str) -> URIRef:
    if (subject_uri := URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])) is None:
        raise ValueError(f"Cannot create subject uri with id: ${subject_id}")
    return subject_uri

def curie_to_uri(
    curie: str,
    prefix_map: Mapping[str, str] = PREFIX_MAP_BIOPORTAL,
) -> URIRef:
    """
    Convert a CURIE (e.g. 'LOINC:2347-3') or prefix-path
    (e.g. 'LOINC/2347-3') to a full URI.

    If the prefix is not found, the input is assumed to already
    be a full URI and is returned as-is.
    """
    for sep in (":", "/"):
        if sep in curie:
            prefix, local = curie.split(sep, 1)
            prefix = prefix.upper()
            if prefix in prefix_map:
                return URIRef(f"{prefix_map[prefix].rstrip('/')}/{local}")

    if is_valid_nt_iri(curie):
        return URIRef(curie)
    
    return URIRef(MEDS_INSTANCES[f"code/{SAFE_CHARS.sub("_", curie)}"])


def update_graph_lazy(
        data, g: Graph, 
        run: Callable[[Any, dict[str, int], int], tuple[URIRef, list[tuple]]], 
) -> list[URIRef]:
    uris = []
    triples = []
    columns = data.columns
    col_idx = {name: i for i, name in enumerate(columns)}

    for row_index, row in enumerate(data.iter_rows()):
        c_uri, _triples = run(row, col_idx, row_index)
        triples.extend(_triples)
        uris.append(c_uri)  # first triple subject is the event URI

        if len(triples) >= BATCH_SIZE:
            g.addN((s, p, o, g) for s, p, o in triples)
            triples.clear()

    if triples:
        g.addN((s, p, o, g) for s, p, o in triples)

    return uris
