from rdflib import Namespace

MEDS = Namespace("https://albertomarfoglia.github.io/meds-ontology#")
MEDS_INSTANCES = "https://albertomarfoglia.github.io/meds-data"
PROV = Namespace("http://www.w3.org/ns/prov#")

PREFIX_MAP_BIOPORTAL = {
    "ATC":      "http://purl.bioontology.org/ontology/ATC/",
    "ICD10PCS": "http://purl.bioontology.org/ontology/ICD10PCS/",
    "ICD10":    "http://purl.bioontology.org/ontology/ICD10CM/",
    "LOINC":    "http://purl.bioontology.org/ontology/LNC/"
}
