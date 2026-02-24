from meds2rdf import MedsRDFConverter

engine = MedsRDFConverter("/home/ubuntu/workspace/meds-to-owl-examples/MIMIC/MEDS_cohort/tmp")

engine.convert(include_dataset_metadata=False, include_codes=True)
