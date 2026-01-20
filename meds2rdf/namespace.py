from rdflib import Namespace

MEDS = Namespace("https://teamheka.github.io/meds-ontology#")
MEDS_INSTANCES = Namespace("https://teamheka.github.io/meds-data/")

PREFIX_MAP_BIOPORTAL = {
    "ATC":      "http://purl.bioontology.org/ontology/ATC",
    "ICD10PCS": "http://purl.bioontology.org/ontology/ICD10PCS",
    "ICD10CM":  "http://purl.bioontology.org/ontology/ICD10CM",
    "LOINC":    "http://purl.bioontology.org/ontology/LNC",
    "RXNORM":   "https://bioportal.bioontology.org/ontologies/RXNORM",
    "ICD9CM":   "https://bioportal.bioontology.org/ontologies/ICD9CM",
    "SNOMED":   "https://bioportal.bioontology.org/ontologies/SNOMED"
}
