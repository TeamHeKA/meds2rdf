import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pyshacl import validate
from rdflib import PROV, RDF, Graph, Literal, URIRef
from rdflib.namespace import XSD

from ..namespace import MEDS, MEDS_INSTANCES, PREFIX_MAP_BIOPORTAL


def run_shacl_validation(graph: Graph, shacl_file: str | Path):
    conforms, results_graph, results_text = validate(
        data_graph=graph,
        shacl_graph=str(shacl_file),
        # inference='rdfs',
        abort_on_first=False,
        debug=False,
    )

    if not conforms:
        raise ValueError(f"SHACL validation failed. {results_text}\n{results_graph}")

    return conforms


def to_literal(value, dtype):
    if isinstance(value, datetime):
        return Literal(value.isoformat(), datatype=XSD.dateTime)
    return Literal(str(value), datatype=dtype)


NT_IRI_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:[^\s<>\"{}|^`\\]+$")

SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def is_valid_nt_iri(iri: str) -> bool:
    return bool(NT_IRI_REGEX.match(iri))


def generate_code_uri(code_str: str, external=False):
    if external:
        return curie_to_uri(code_str)

    return URIRef(MEDS_INSTANCES[f"code/{SAFE_CHARS.sub('_', code_str.replace('//', '_'))}"])


def generate_code(
    code_str: str, dataset_uri: URIRef | None = None, external=False
) -> tuple[URIRef, list]:
    triples = []
    code_uri = generate_code_uri(code_str, external)
    triples.append((code_uri, RDF.type, MEDS.Code))
    triples.append((code_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))
    if dataset_uri:
        triples.append((code_uri, PROV.wasDerivedFrom, dataset_uri))
    return (code_uri, triples)


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

    return URIRef(MEDS_INSTANCES[f"code/{SAFE_CHARS.sub('_', curie)}"])


def sanitize_text(s: str, mode: str = "escape_newlines") -> str:
    """
    Sanitize a text string for safe N-Triples serialization.

    mode:
      - "escape_newlines":   replace actual newline chars with two-char '\\n' sequences
      - "unicode_escape":    use python unicode-escape for control chars
                             (not recommended for display)
    """
    if s is None:
        raise RuntimeError("Text to sanitize can not be None")

    if mode == "escape_newlines":
        # Preserve backslashes correctly: first escape existing backslashes,
        # then convert newlines into literal backslash + 'n' sequences.
        # This makes the literal contain the two characters '\' and 'n'.
        # Note: serializers may further escape backslashes when producing N-Triples,
        # but the result will remain one physical line.
        return " ".join(
            s.replace("\\", "\\\\")
            .replace("\r\n", "\n")
            .replace("\t", "\n")
            .replace("\r", "\n")
            .replace('"', "")
            .split()
        )

    if mode == "unicode_escape":
        # This returns an ASCII str where control chars become \n, \t, \uXXXX etc.
        return s.encode("unicode_escape").decode("ascii")

    raise ValueError("unknown sanitize mode: " + repr(mode))
