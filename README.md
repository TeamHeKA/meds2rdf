# meds2rdf

**Convert MEDS datasets into RDF using the MEDS Ontology**

[MEDS](https://medical-event-data-standard.github.io/) (Medical Event Data Standard) is a standard schema for representing longitudinal medical event data. This library, `meds2rdf`, converts MEDS-compliant datasets into RDF triples using the [MEDS Ontology](https://albertomarfoglia.github.io/meds-ontology).

## Features

- Convert MEDS datasets (Data, Codes, Labels, Subject Splits) into RDF.
- Supports all MEDS value modalities: numeric, text, images, waveforms.
- Fully links:
  - Measurements to Subjects
  - Codes to metadata
  - Labels to prediction samples
  - Subjects to splits
  - Measurements and Codes to dataset metadata
- Outputs RDF in Turtle format (`.ttl`) ready for use with standard RDF tools.

## Installation
From the repo root:
```bash
git clone https://github.com/albertomarfoglia/meds2rdf.git
cd meds2rdf
pip install -e .
```
You can install it directly from GitHub:
```bash
pip install git+https://github.com/albertomarfoglia/meds2rdf.git
```

## How to Use

```python
from meds2rdf import MedsRDFConverter

# Initialize the converter with the path to your MEDS dataset directory
converter = MedsRDFConverter("/path/to/your/meds_dataset")

# Convert the dataset into an RDF graph
graph = converter.convert(
    include_dataset_metadata=True,
    include_codes=True,
    include_labels=True,
    include_splits=True,
    generate_code_nodes=False
)

# Serialize the graph to different formats
graph.serialize(destination="output_dataset.ttl", format="turtle")
graph.serialize(destination="output_dataset.xml", format="xml")
graph.serialize(destination="output_dataset.nt", format="nt")

print("Conversion complete! RDF files saved.")
```

### Notes

* Make sure your MEDS dataset directory contains the expected structure:

  * `metadata/dataset.json`
  * `metadata/codes.parquet` (optional)
  * `metadata/subject_splits.parquet` (optional)
  * `data/` folder with Parquet files
  * `labels/` folder with label Parquet files
* The `convert` method returns an `rdflib.Graph` object that you can further manipulate or serialize.