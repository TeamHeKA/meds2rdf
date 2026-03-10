from rdflib import Namespace

MEDS = Namespace("https://teamheka.github.io/meds-ontology#")
MEDS_INSTANCES = Namespace("https://teamheka.github.io/meds-data/")

PREFIX_MAP_BIOPORTAL = {
    "ATC":      "http://purl.bioontology.org/ontology/ATC",
    "ICD10PCS": "http://purl.bioontology.org/ontology/ICD10PCS",
    "ICD10CM":  "http://purl.bioontology.org/ontology/ICD10CM",
    "LOINC":    "http://purl.bioontology.org/ontology/LNC",
    "RXNORM":   "http://purl.bioontology.org/ontology/RXNORM",
    "ICD9CM":   "http://purl.bioontology.org/ontology/ICD9CM",
    "SNOMED":   "http://purl.bioontology.org/ontology/SNOMED"
}
