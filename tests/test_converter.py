# tests/test_shacl_validation.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
from rdflib import Graph

from meds2rdf.converter import MedsRDFConverter
from meds2rdf.utils.rdf_utils import run_shacl_validation

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
        "subject_id": 22222222,
        "time": "2025-01-01T05:30:00",
        "code": "LAB//GLUCOSE",
        "numeric_value": 120.5,
        "text_value": None,
    },
    # Subject 1 — event with image value modality
    {
        "subject_id": 33333333,
        "time": "2025-01-02T12:30:05",
        "code": "RADIOLOGY//CHEST_XRAY",
        "numeric_value": None,
        "text_value": None,
        "image_path": "/images/xray_11111111_0001.png",
    },
    # Subject 2 — minimal data
    {
        "subject_id": 44444444,
        "time": "2025-01-03T00:00:00",
        "code": "DEMOGRAPHICS//AGE",
        "numeric_value": 60,
    },
]


mock_codes = [
    {
        "code": "DEMOGRAPHICS//GENDER",
        "description": "Administrative sex of patient",
        "parent_codes": ["ICD10:AAAA"],
    },
    {"code": "DEMOGRAPHICS//AGE", "description": "Age in years", "parent_codes": ["ICD10:AAAA"]},
    {
        "code": "LAB//GLUCOSE",
        "description": "Blood glucose level",
        "parent_codes": ["ICD10:AAAA", "ICD10:BBB"],
    },
    {
        "code": "RADIOLOGY//CHEST_XRAY",
        "description": "AP/PA Chest X-ray",
        "parent_codes": ["ICD10:AAAA"],
    },
    {
        "code": "DEMOGRAPHICS//ROOT",
        "description": "Demographic information root",
        "parent_codes": [],
    },
    {
        "code": "LAB//CHEMISTRY",
        "description": "Chemistry lab panel",
        "parent_codes": ["ICD10:AAAA"],
    },
    {"code": "LAB//ROOT", "description": "Laboratory results root", "parent_codes": []},
    {"code": "RADIOLOGY//ROOT", "description": "Radiology studies root", "parent_codes": []},
]

mock_splits = [
    {"subject_id": 11111111, "split": "train"},
    {"subject_id": 22222222, "split": "train"},
    {"subject_id": 33333333, "split": "tuning"},
    {"subject_id": 44444444, "split": "held_out"},
]


mock_labels = [
    # boolean label
    {"subject_id": 11111111, "prediction_time": "2025-01-02T00:00:00", "boolean_value": True},
    # integer label
    {"subject_id": 11111111, "prediction_time": "2025-01-02T00:00:00", "integer_value": 3},
    # float label
    {"subject_id": 22222222, "prediction_time": "2025-01-03T05:00:00", "float_value": 12.7},
    # categorical label
    {
        "subject_id": 33333333,
        "prediction_time": "2025-01-04T10:00:00",
        "categorical_value": "SEVERE",
    },
]

# Path to the remote SHACL shapes you want to validate against:
SHACL_SHAPES_URL = "https://raw.githubusercontent.com/TeamHeKA/meds-ontology/refs/tags/v1.0.2/shacl/meds-shapes.ttl"


def fake_task_dir(name: str):
    task = MagicMock(spec=Path)
    task.is_dir.return_value = True
    task.name = name
    task.rglob.return_value = [Path("dummy/path/labels/task1/train/file.parquet")]

    return task


def _fake_task_dir(name):
    p = MagicMock(spec=Path)
    p.is_dir.return_value = True
    p.name = name
    p.iterdir.return_value = []  # no splits inside for now
    p.rglob.return_value = []  # no parquet files
    return p


def test_convert_and_validate_shacl(monkeypatch, tmp_path):
    """
    Tests that the output RDF graph from MedsRDFConverter conforms to the MEDS SHACL shapes.
    """
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.iterdir") as mock_iterdir,
        patch("polars.scan_parquet") as mock_scan,
    ):
        mock_iterdir.return_value = [_fake_task_dir("task1")]

        mock_scan.side_effect = [
            pl.DataFrame(mock_data).lazy(),  # data
            pl.DataFrame(mock_codes).lazy(),  # codes
            pl.DataFrame(mock_splits).lazy(),  # splits
            pl.DataFrame(mock_labels).lazy(),  # labels
        ]

        engine = MedsRDFConverter(tmp_path)
        temp_dir = tmp_path / "metadata"
        temp_dir.mkdir()
        with open(temp_dir / "dataset.json", "w", encoding="utf-8") as f:
            json.dump(mock_dataset_metadata, f, indent=4, ensure_ascii=False)

        data_graph = None
        # Context manager ensures automatic cleanup
        with engine:
            data_graph = engine.convert(
                include_dataset_metadata=True,
                include_codes=True,
                include_labels=True,
                include_splits=True,
                output_dir=tmp_path,
            )

        if data_graph is not None:
            run_shacl_validation(data_graph, SHACL_SHAPES_URL)

    # Sanity check — we *have* an rdflib.Graph
    assert isinstance(data_graph, Graph)
