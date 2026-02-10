from app.services.ontology_exporter import OntologyExporter
from app.services.owl_parser import OWLParser
import os


def test_prefix_roundtrip():
    # 1. Setup mock data
    classes = [
        {"name": "Material", "label": "Material", "dataProperties": ["baseUnit:string"]}
    ]
    relationships = []

    exporter = OntologyExporter()
    ttl_content = exporter.export_to_ttl(classes, relationships)

    print("--- Exported TTL (First time) ---")
    print(ttl_content)

    # Verify no 'prop_' in TTL URI if possible (checking string content)
    # The URI should be http://example.org/ontology#baseUnit
    assert "prop_baseUnit" not in ttl_content
    assert "baseUnit" in ttl_content

    # 2. Simulate Import
    parser = OWLParser()
    parser.load_from_string(ttl_content)
    imported_props = parser.extract_properties()

    print("\n--- Imported Properties ---")
    print(imported_props)

    # Name should be 'baseUnit', not 'prop_baseUnit'
    assert imported_props[0]["name"] == "baseUnit"

    # 3. Simulate existing polluted TTL
    polluted_ttl = """
@prefix base: <http://example.org/ontology#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

base:Material a owl:Class .

base:prop_prop_pollutedProp a owl:DatatypeProperty ;
    rdfs:domain base:Material .
"""
    parser2 = OWLParser()
    parser2.load_from_string(polluted_ttl)
    polluted_props = parser2.extract_properties()

    print("\n--- Polluted Import (Extracted Name) ---")
    print(polluted_props)

    # Should strip multiple 'prop_'
    assert polluted_props[0]["name"] == "pollutedProp"

    print("\nVerification successful!")


if __name__ == "__main__":
    test_prefix_roundtrip()
