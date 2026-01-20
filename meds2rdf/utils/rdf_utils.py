from pathlib import Path
from typing import Callable, Iterable, Mapping
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
        code_uri = URIRef(MEDS_INSTANCES[f"code/{quote(code_str).replace("//", "_")}"])

    if node_exist(graph, node=code_uri) is False:
        graph.add((code_uri, RDF.type, MEDS.Code))
        graph.add((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
        if dataset_uri:
            graph.add((code_uri, PROV.wasDerivedFrom, dataset_uri))
        
    return code_uri

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
    if curie is None: 
        return 
    
    for sep in (":", "/"):
        if sep in curie:
            prefix, local = curie.split(sep, 1)
            if prefix in prefix_map:
                return URIRef(f"{prefix_map[prefix].rstrip('/')}/{local}")

    return URIRef(curie)
