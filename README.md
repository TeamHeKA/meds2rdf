<h1 align="center">MEDS2RDF</h1>

<p align="center">
  <img src="https://img.shields.io/github/v/release/TeamHeKA/meds2rdf" alt="Latest Release"/>
  <img src="https://github.com/TeamHeKA/meds2rdf/actions/workflows/tests.yml/badge.svg" alt="Tests"/>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12"/>
  <img src="https://img.shields.io/github/license/TeamHeKA/meds2rdf" alt="License"/>
  <a href="https://doi.org/10.5281/zenodo.17953581"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.17953581.svg" alt="DOI"></a>
</p>

**Convert MEDS datasets into RDF using the MEDS Ontology**

[MEDS](https://medical-event-data-standard.github.io/) (Medical Event Data Standard) is a standard schema for representing longitudinal medical event data. This library, `meds2rdf`, converts MEDS-compliant datasets into RDF triples using the [MEDS Ontology](https://teamheka.github.io/meds-ontology).

---

## Features

- Convert MEDS datasets (Data, Codes, Labels, Subject Splits) into RDF.
- Supports all MEDS value modalities: numeric, text, images, waveforms.
- Fully links:
  - Events to Subjects
  - Codes to metadata
  - Labels to prediction samples
  - Subjects to splits
  - Events and Codes to dataset metadata
- Outputs RDF in Turtle, XML, or N-Triples format.
- Optional persistent store via SQLite (requires `rdflib-sqlalchemy`).

---

## Installation

Clone and install the package in editable mode:

```bash
git clone https://github.com/TeamHeKA/meds2rdf.git
cd meds2rdf
pip install -e .
````

Or install directly from GitHub:

```bash
pip install git+https://github.com/TeamHeKA/meds2rdf.git
```

If you want **persistent SQLite-backed RDF storage**, also install:

```bash
pip install rdflib-sqlalchemy
```

---

## Usage

### In-Memory Graph (default)

```python
from meds2rdf import MedsRDFConverter

# Initialize the converter (in-memory)
converter = MedsRDFConverter("/path/to/meds_dataset")

# Convert the dataset
converter.convert(
    include_dataset_metadata=True,
    include_codes=True,
    include_labels=True,
    include_splits=True
)

# Serialize to different formats
converter.to_turtle("output_dataset.ttl")
converter.to_xml("output_dataset.xml")
converter.to_nt("output_dataset.nt")

# Close resources
converter.close()
```

---

### Persistent SQLite Store

```python
from meds2rdf import MedsRDFConverter

# Requires `rdflib-sqlalchemy` installed
converter = MedsRDFConverter(
    "/path/to/meds_dataset",
    persistent_store=True,
)

# Context manager ensures automatic cleanup
with converter:
    graph = converter.convert(include_labels=True)
    converter.to_turtle("output_dataset.ttl")
```

## Notes

* The MEDS dataset directory must follow the standard structure:

  * `metadata/dataset.json`
  * `metadata/codes.parquet` (optional)
  * `metadata/subject_splits.parquet` (optional)
  * `data/` folder with Parquet files
  * `labels/` folder with label Parquet files

* The `convert` method returns an `rdflib.Graph` object that can be further manipulated or serialized.

* For persistent stores, the `store_path` points to **one SQLite database file** that contains the full graph. You do not need multiple files unless you want separate graphs.

---

## Running Tests

This project uses **pytest**.

### Install development dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

pip install -e .[dev]
```

Or install pytest manually:

```bash
pip install pytest
```

> Installing in **editable mode (`-e`)** is important so Python can import the `meds2rdf` package during tests.

### Run the full test suite

```bash
pytest
```

---

## Cite this Repository

If you use `meds2rdf` in your research, please cite it as follows:

### BibTeX

```bibtex
@software{meds2rdf,
  title        = {meds2rdf: Converting MEDS Datasets to RDF Using the MEDS Ontology},
  author       = {{Alberto Marfoglia and Contributors}},
  year         = {2025},
  url          = {https://doi.org/10.5281/zenodo.17953580},  note         = {Python library for converting MEDS-compliant datasets into RDF}
}
```