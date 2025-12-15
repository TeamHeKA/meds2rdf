from setuptools import setup, find_packages

setup(
    name="meds2rdf",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "polars==1.36.0",
        "polars-runtime-32==1.36.0",
        "pyparsing==3.2.5",
        "rdflib==7.5.0",
    ],
    python_requires='>=3.8',
    description="Convert MEDS datasets into RDF using the MEDS Ontology",
    url="https://github.com/TeamHeKA/meds2rdf",
    author="Alberto Marfoglia",
    author_email="a.marfoglia@hotmail.it",
    license="MIT",
)
