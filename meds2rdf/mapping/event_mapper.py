from rdflib import URIRef, Literal
from rdflib.namespace import RDF, XSD, PROV

from ..namespace import MEDS, MEDS_INSTANCES
from ..utils.rdf_utils import generate_code

_literals_dict = {
    "time": (MEDS.time, XSD.dateTime),
    "numeric_value": (MEDS.numericValue, XSD.double),
    "text_value": (MEDS.textValue, XSD.string),
}

def map_event(
    row: tuple,
    col_idx: dict[str, int],
    row_index: int,
    dataset_uri: URIRef | None = None
) -> list[tuple[URIRef, URIRef, URIRef]]:
    triples = []
    subject_id = row[col_idx["subject_id"]]

    event_uri = URIRef(MEDS_INSTANCES[f"event/{subject_id}_{row_index}"])
    triples.append((event_uri, RDF.type, MEDS.Event))

    subject_uri = URIRef(MEDS_INSTANCES[f"subject/{subject_id}"])
    triples.append((subject_uri, RDF.type, MEDS.Subject))
    triples.append((subject_uri, MEDS.subjectId, Literal(str(subject_id), datatype=XSD.string)))
    triples.append((event_uri, MEDS.hasSubject, subject_uri))

    # Code
    code_str = row[col_idx["code"]]
    triples.append((event_uri, MEDS.codeString, Literal(str(code_str), datatype=XSD.string)))

    code_uri, code_triples = generate_code(code_str=code_str)
    triples.extend(code_triples)
    triples.append((event_uri, MEDS.hasCode, code_uri))

    if dataset_uri:
        triples.append((event_uri, PROV.wasDerivedFrom, dataset_uri))

    # Literals
    for col_name, (predicate, dtype) in _literals_dict.items():
        if col_name in col_idx:
            val = row[col_idx[col_name]]
            if val is not None:
                triples.append((event_uri, predicate,
                                Literal(val, datatype=dtype)))

    return triples
