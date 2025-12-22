from pathlib import Path
from typing import Callable, Iterable
from rdflib import Literal, RDF, URIRef, Graph, PROV
from rdflib.namespace import XSD
from datetime import datetime
from typing import Optional, Callable, Iterable
from ..namespace import MEDS, MEDS_INSTANCES, PREFIX_MAP_BIOPORTAL

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

def if_column_is_present(column_name, source, callback: Callable[[str], Graph]):
    value = source.get(column_name)
    if value is None:
        return
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for v in value:
            callback(v)
    else:
        callback(str(value))

from urllib.parse import quote

def add_code(code_str: str, graph: Graph, dataset_uri: Optional[URIRef] = None, external = False):
    if external: 
        code_uri = curie_to_uri(code_str)
    else: 
        code_uri = URIRef(MEDS_INSTANCES[f"code/{quote(code_str)}"])

    graph.add((code_uri, RDF.type, MEDS.Code))
    graph.add((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))

    if dataset_uri:
        graph.add((code_uri, PROV.wasDerivedFrom, dataset_uri))
        
    return code_uri

def to_subject_node(subject_id: str) -> URIRef:
    if (subject_uri := URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])) is None:
        raise ValueError(f"Cannot create subject uri with id: ${subject_id}")
    return subject_uri

def curie_to_uri(curie: str, prefix_map: dict = PREFIX_MAP_BIOPORTAL) -> URIRef:
    prefix, local = curie.split(":", 1)
    if prefix not in prefix_map:
        raise ValueError(f"Unknown prefix: {prefix}")
    return URIRef(f"{prefix_map[prefix]}/{local}")
