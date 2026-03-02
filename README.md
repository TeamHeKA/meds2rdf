# MEDS2RDF

<p align="center">
  <img src="https://img.shields.io/github/v/release/TeamHeKA/meds2rdf" alt="Latest Release"/>
  <img src="https://github.com/TeamHeKA/meds2rdf/actions/workflows/tests.yml/badge.svg" alt="Tests"/>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12"/>
  <img src="https://img.shields.io/github/license/TeamHeKA/meds2rdf" alt="License"/>
  <a href="https://doi.org/10.5281/zenodo.17953581"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.17953581.svg" alt="DOI"></a>
</p>

Convert MEDS datasets into RDF using the MEDS Ontology.

`meds2rdf` turns MEDS-compliant datasets into RDF triples (N-Triples / Turtle / RDF/XML), with a modern streaming, sink-based API that is memory-friendly and production-ready.


## What changed (short)

`meds2rdf` now provides:

* A **Sink-based API**: producers (converter/mappers) push triples into a `TripleSink` — decouples generation from persistence.
* A **batching high-performance sink** and a streaming **N-Triples (optionally gzipped) sink**.
* A typed `Config` + `MEDSSchema` enum for schema selection.

## Installation

```bash
git clone https://github.com/TeamHeKA/meds2rdf.git
cd meds2rdf
pip install -e .
```

Install dev/test deps:

```bash
pip install -e .[dev]
```

## API (overview)

### Key types

* `meds2rdf.sinks.base.TripleSink` — abstract sink interface. Implementations: `GraphSink`, `NTriplesSink` (gz supported), `batch sinks`.
* `meds2rdf.config.Config` — conversion configuration (which MEDS schemas to export, batch size, etc.).
* `meds2rdf.config.MEDSSchema` — enum values: `DATASET_METADATA`, `CODES`, `LABELS`, `SPLITS`.
* `meds2rdf.converter.MedsRDFConverter` — stateless converter; it *produces* triples and forwards them to a `TripleSink`.

### New `convert` signature (breaking change vs older versions <= 1.0.1)

```python
def convert(self, sink: TripleSink, cfg: Config) -> None:
    ...
```

`cfg` controls which MEDS schemas are exported and batch behaviour. The converter is **stateless**; the sink controls persistence.

---

## Usage examples

### 1) Stream to an `nt.gz` file (recommended for large exports)

```python
from pathlib import Path
from meds2rdf.sinks.ntriples_sink import NTriplesSink
from meds2rdf.config import Config, MEDSSchema
from meds2rdf.converter import MedsRDFConverter

# prepare sink (gzipped NT)
sink = NTriplesSink(Path("out/meds_events.nt.gz"), batch_size=100_000, gzip_mode=True)

cfg = Config(schemas={MEDSSchema.DATASET_METADATA, MEDSSchema.LABELS}, batch_size=100_000)

converter = MedsRDFConverter("/path/to/meds_dataset")
converter.convert(sink=sink, cfg=cfg)
# sink.close() is called by convert(), but it's ok to call again to be explicit
sink.close()
```

### 2) Populate an in-memory `rdflib.Graph` (useful for tests / small datasets)

```python
from rdflib import Graph
from meds2rdf.sinks.graph_sink import GraphSink
from meds2rdf.config import Config, MEDSSchema
from meds2rdf.converter import MedsRDFConverter

graph = Graph()
sink = GraphSink(graph, batch_size=50_000)

cfg = Config(schemas={MEDSSchema.CODES, MEDSSchema.SPLITS}, batch_size=50_000)

conv = MedsRDFConverter("/path/to/meds_dataset")
conv.convert(sink=sink, cfg=cfg)

# graph now contains triples
print(len(graph))
```

## Migration notes (old → new)

Old call:

```py
converter.convert(
    include_dataset_metadata=True,
    include_codes=True,
    include_labels=True,
    include_splits=True
)
```

New call:

```py
from meds2rdf.config import Config, MEDSSchema

cfg = Config(schemas={MEDSSchema.DATASET_METADATA,
                      MEDSSchema.CODES,
                      MEDSSchema.LABELS,
                      MEDSSchema.SPLITS},
             batch_size=256_000)

converter.convert(sink=my_sink, cfg=cfg)
```

---

## Where to hook custom storage

Implement `meds2rdf.sinks.base.TripleSink`:

```python
class MyCustomSink(TripleSink):
    def add(self, s, p, o): ...
    def add_many(self, triples): ...
    def flush(self): ...
    def close(self): ...
```

Then pass an instance to `convert()`.

Examples shipped: `GraphSink`, `NTriplesSink` (gz supported), `batch` variations.

---

## Performance tips

* Use gzipped NT output for fast streaming + smaller disk footprint.
* Tune `batch_size` depending on memory & target sink (100k–500k is a good starting point).
* Use `GraphSink` only for small–medium datasets; very large graphs are best saved to NT files or loaded via a triplestore.

## Tests

Run the test suite:

```bash
pytest
```

## Cite this repository

If you use `meds2rdf` in your research, please cite it (DOI on Zenodo and releases on TeamHeKA).

BibTeX:

```bibtex
@software{meds2rdf,
  title        = {meds2rdf: Converting MEDS Datasets to RDF Using the MEDS Ontology},
  author       = {{Alberto Marfoglia and Contributors}},
  year         = {2025},
  url          = {https://doi.org/10.5281/zenodo.17953580},
  note         = {Python library for converting MEDS-compliant datasets into RDF}
}
```
