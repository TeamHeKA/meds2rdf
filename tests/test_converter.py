# tests/test_shacl_validation.py
import pytest
from rdflib import Graph
from pyshacl import validate
from meds2rdf.converter import MedsRDFConverter

# You can reuse your mocks from previous tests:
mock_dataset_metadata = {
    "dataset_name": "ComplexMEDS-Demo",
    "dataset_version": "4.1.2",
    "etl_name": "Hospital_ETL_v9",
    "etl_version": "9.0.1",
    "meds_version": "0.4.0",
    "created_at": "2025-02-14T08:45:10.123456",
    "license": "CC BY-NC 4.0",
    "location_uri": "s3://hospital-bucket/meds/",
    "description_uri": "https://hospital.org/meds-docs",
    "raw_source_id_columns": ["patient_id", "encounter_id"],
    "site_id_columns": ["site"],
    "code_modifier_columns": ["unit"],
    "additional_value_modality_columns": ["image_path"],
    "other_extension_columns": ["flag"],
    "subject_id_columns": ["subject_id"],
}

mock_data = [
    # Subject 1 — static demographic event (time=null)
    {
        "subject_id": 11111111,
        "time": None,
        "code": "DEMOGRAPHICS//GENDER",
        "text_value": "F",
        "numeric_value": None,
    },

    # Subject 1 — age
    {
        "subject_id": 11111111,
        "time": "2025-01-01T00:00:00",
        "code": "DEMOGRAPHICS//AGE",
        "numeric_value": 45,
        "text_value": None,
    },

    # Subject 1 — lab event with unit modifier
    {
        "subject_id": 11111111,
        "time": "2025-01-01T05:30:00",
        "code": "LAB//GLUCOSE",
        "numeric_value": 120.5,
        "text_value": None,
    },

    # Subject 1 — event with image value modality
    {
        "subject_id": 11111111,
        "time": "2025-01-02T12:30:05",
        "code": "RADIOLOGY//CHEST_XRAY",
        "numeric_value": None,
        "text_value": None,
        "image_path": "/images/xray_11111111_0001.png"
    },

    # Subject 2 — minimal data
    {
        "subject_id": 22222222,
        "time": "2025-01-03T00:00:00",
        "code": "DEMOGRAPHICS//AGE",
        "numeric_value": 60,
    },
]


mock_codes = [
    {
        "code": "DEMOGRAPHICS//GENDER",
        "description": "Administrative sex of patient",
        "parent_codes": ["ICD10:AAAA"]
    },
    {
        "code": "DEMOGRAPHICS//AGE",
        "description": "Age in years",
        "parent_codes": ["ICD10:AAAA"]
    },
    {
        "code": "LAB//GLUCOSE",
        "description": "Blood glucose level",
        "parent_codes": ["ICD10:AAAA", "ICD10:BBB"]
    },
    {
        "code": "RADIOLOGY//CHEST_XRAY",
        "description": "AP/PA Chest X-ray",
        "parent_codes": ["ICD10:AAAA"]
    },
    {
        "code": "DEMOGRAPHICS//ROOT",
        "description": "Demographic information root",
        "parent_codes": []
    },
    {
        "code": "LAB//CHEMISTRY",
        "description": "Chemistry lab panel",
        "parent_codes": ["ICD10:AAAA"]
    },
    {
        "code": "LAB//ROOT",
        "description": "Laboratory results root",
        "parent_codes": []
    },
    {
        "code": "RADIOLOGY//ROOT",
        "description": "Radiology studies root",
        "parent_codes": []
    }
]

mock_splits = [
    {"subject_id": 11111111, "split": "train"},
    {"subject_id": 22222222, "split": "train"},
    {"subject_id": 33333333, "split": "tuning"},
    {"subject_id": 44444444, "split": "held_out"},
]


mock_labels = [
    # boolean label
    {
        "subject_id": 11111111,
        "prediction_time": "2025-01-02T00:00:00",
        "boolean_value": True
    },
    # integer label
    {
        "subject_id": 11111111,
        "prediction_time": "2025-01-02T00:00:00",
        "integer_value": 3
    },
    # float label
    {
        "subject_id": 22222222,
        "prediction_time": "2025-01-03T05:00:00",
        "float_value": 12.7
    },
    # categorical label
    {
        "subject_id": 33333333,
        "prediction_time": "2025-01-04T10:00:00",
        "categorical_value": "SEVERE"
    },
]

# Path to the remote SHACL shapes you want to validate against:
SHACL_SHAPES_URL = "https://raw.githubusercontent.com/HeKaMEDS/meds-ontology/refs/heads/main/shacl/meds-shapes.ttl"


def test_convert_and_validate_shacl(monkeypatch):
    """
    Tests that the output RDF graph from MedsRDFConverter conforms to the MEDS SHACL shapes.
    """

    # -- 1. Mock out filesystem + read_parquet just like in your previous test
    import polars as pl
    from pathlib import Path
    import json
    from unittest.mock import MagicMock, mock_open, patch

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_dataset_metadata))), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("polars.read_parquet") as mock_pl_read:

        # Make Polars return our mock objects
        mock_pl_read.side_effect = [
            MagicMock(to_dicts=lambda: mock_data),    # data/**/*.parquet
            MagicMock(to_dicts=lambda: mock_codes),   # codes
            MagicMock(to_dicts=lambda: mock_splits),  # splits
            MagicMock(to_dicts=lambda: mock_labels),  # labels
        ]

        converter = MedsRDFConverter("dummy/path")
        data_graph = converter.convert(
            include_dataset_metadata=True,
            include_codes=True,
            include_labels=True,
            include_splits=True,
        )

    # Sanity check — we *have* an rdflib.Graph
    assert isinstance(data_graph, Graph)

    # -- 2. Load shapes graph
    shapes_graph = Graph()
    shapes_graph.parse(SHACL_SHAPES_URL, format="ttl")

    data_graph.print()

    # -- 3. Validate with pySHACL
    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",      # optional
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )

    print(results_text)  # helpful if the test fails

    assert conforms, "SHACL validation failed:\n" + results_text
