# backend/app/services/ontology_exporter.py
"""
Ontology Export Service

Converts the internal PostgreSQL ontology representation to a standard OWL file in Turtle format.
"""

from rdflib import Graph, Literal, RDF, RDFS, OWL, Namespace, XSD
from typing import List, Dict, Any

# Define a default namespace for the ontology
BASE_NS = Namespace("http://example.org/ontology#")
XSD_NS = Namespace("http://www.w3.org/2001/XMLSchema#")


class OntologyExporter:
    """Service to export ontology data as OWL/Turtle."""

    def __init__(self):
        self.graph = Graph()
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("base", BASE_NS)

    def export_to_ttl(self, classes: List[Dict], relationships: List[Dict]) -> str:
        """
        Convert internal classes and relationships to Turtle format.

        Args:
            classes: List of dicts with 'name', 'label', 'dataProperties'.
            relationships: List of dicts with 'source', 'type', 'target'.

        Returns:
            str: Turtle formatted string.
        """
        # Add classes
        for cls_data in classes:
            class_uri = BASE_NS[cls_data["name"]]
            self.graph.add((class_uri, RDF.type, OWL.Class))
            # Add labels (aliases)
            labels = cls_data.get("label", [])
            if isinstance(labels, str):
                labels = [labels]
            for label in labels:
                if label:
                    self.graph.add((class_uri, RDFS.label, Literal(label)))

            # Add data properties
            for prop in cls_data.get("dataProperties", []):
                # property format might be "name:string" or just "name"
                parts = prop.split(":")
                prop_name = parts[0]
                prop_type = parts[1] if len(parts) > 1 else "string"

                prop_uri = BASE_NS[prop_name]
                self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                self.graph.add((prop_uri, RDFS.domain, class_uri))

                # Add range based on type
                if prop_type == "int" or prop_type == "integer":
                    self.graph.add((prop_uri, RDFS.range, XSD.integer))
                elif prop_type == "float" or prop_type == "double":
                    self.graph.add((prop_uri, RDFS.range, XSD.double))
                elif prop_type == "boolean":
                    self.graph.add((prop_uri, RDFS.range, XSD.boolean))
                elif prop_type == "date":
                    self.graph.add((prop_uri, RDFS.range, XSD.date))
                elif prop_type == "datetime":
                    self.graph.add((prop_uri, RDFS.range, XSD.dateTime))
                else:
                    self.graph.add((prop_uri, RDFS.range, XSD.string))

        # Add object properties (relationships)
        for rel_data in relationships:
            prop_uri = BASE_NS[rel_data["type"]]
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.domain, BASE_NS[rel_data["source"]]))
            self.graph.add((prop_uri, RDFS.range, BASE_NS[rel_data["target"]]))

        return self.graph.serialize(format="turtle")
