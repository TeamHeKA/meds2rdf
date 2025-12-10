from typing import Callable, Iterable
from rdflib import Literal, RDF, Node, URIRef, Graph
from rdflib.namespace import XSD
from datetime import datetime
from typing import Optional, Callable, Iterable
from ..namespace import MEDS, MEDS_INSTANCES, PROV, PREFIX_MAP_BIOPORTAL

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

def add_code(code_str: str, graph: Graph, dataset_uri: Optional[URIRef] = None):
    code_uri = URIRef(base=MEDS_INSTANCES, value=f"code/{code_str.replace(" ", "%20")}")
    graph.add((code_uri, RDF.type, MEDS.Code))
    graph.add((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    if dataset_uri:
        graph.add((code_uri, PROV.wasDerivedFrom, dataset_uri))
    return code_uri

def to_subject_node(subject_id: str) -> URIRef:
    if (subject_uri := URIRef(base=MEDS_INSTANCES, value=f"subject/{subject_id}")) is None:
        raise ValueError(f"Cannot create subject uri with id: ${subject_id}")
    return subject_uri

def curie_to_uri(curie: str, prefix_map: dict = PREFIX_MAP_BIOPORTAL) -> str:
    prefix, local = curie.split(":", 1)
    if prefix not in prefix_map:
        raise ValueError(f"Unknown prefix: {prefix}")
    return prefix_map[prefix] + local
