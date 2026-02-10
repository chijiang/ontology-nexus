import asyncio
import os
import sys
from sqlalchemy import text, select
from rdflib import Graph, URIRef, RDF, RDFS, OWL, XSD

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pg_graph_storage import PGGraphStorage
from app.services.ontology_exporter import OntologyExporter
from app.services.pg_graph_importer import PGGraphImporter
from app.services.owl_parser import OWLParser
from app.core.database import async_session
from app.models.graph import SchemaClass


async def test_ontology_features():
    print("Starting verification for property types and aliases...")
    async with async_session() as db:
        storage = PGGraphStorage(db)
        exporter = OntologyExporter()
        importer = PGGraphImporter(db)

        # 1. Clean up
        await db.execute(text("DELETE FROM schema_classes"))
        await db.execute(text("DELETE FROM graph_entities"))
        await db.execute(text("DELETE FROM schema_relationships"))
        await db.commit()

        # 2. Add a class with multiple aliases and typed properties
        class_name = "Product"
        aliases = ["Goods", "Item"]
        data_props = [
            "price:float",
            "stock:int",
            "is_active:boolean",
            "created_at:datetime",
        ]

        await storage.add_ontology_class(
            class_name, label=aliases, data_properties=data_props
        )
        print(f"Added class {class_name} with aliases {aliases}")

        # 3. Export to TTL
        classes = await storage.get_ontology_classes()
        relationships = await storage.get_ontology_relationships()
        ttl_content = exporter.export_to_ttl(classes, relationships)

        print("\n--- Exported TTL (snippet) ---")
        print(ttl_content[:500] + "...")
        print("----------------------------\n")

        # Verify TTL contents
        g = Graph().parse(data=ttl_content, format="turtle")
        ns = "http://example.org/ontology#"
        class_uri = URIRef(f"{ns}{class_name}")

        # Check labels
        labels = [str(o) for s, p, o in g.triples((class_uri, RDFS.label, None))]
        print(f"Labels in TTL: {labels}")
        assert all(
            a in labels for a in aliases
        ), f"Aliases {aliases} missing from TTL labels {labels}"

        # Check property ranges
        price_uri = URIRef(f"{ns}price")
        stock_uri = URIRef(f"{ns}stock")
        is_active_uri = URIRef(f"{ns}is_active")

        range_price = g.value(price_uri, RDFS.range)
        range_stock = g.value(stock_uri, RDFS.range)
        range_is_active = g.value(is_active_uri, RDFS.range)

        print(f"Price range: {range_price}")
        print(f"Stock range: {range_stock}")
        print(f"IsActive range: {range_is_active}")

        assert str(range_price).endswith("double") or str(range_price).endswith("float")
        assert str(range_stock).endswith("integer")
        assert str(range_is_active).endswith("boolean")

        # 4. Import TTL back
        # Clear again
        await db.execute(text("DELETE FROM schema_classes"))
        await db.commit()

        # Use parser as argument
        parser = OWLParser(ttl_content.encode("utf-8"))
        await importer.import_schema(parser)

        # Verify imported classes
        imported_classes = await storage.get_ontology_classes()
        imported_class = next(c for c in imported_classes if c["name"] == class_name)

        print(f"\nImported class labels: {imported_class['label']}")
        assert all(a in imported_class["label"] for a in aliases)

        print(f"Imported class properties: {imported_class['dataProperties']}")
        for dp in data_props:
            # Note: imported properties might be rearranged or slightly different in range suffix
            # But the verification script added "price:float" and backend parsed "float"
            assert dp in imported_class["dataProperties"]

        # 5. Test instance labels as aliases
        node_name = "p1"
        instance_ttl = f"""
        @prefix : <{ns}> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        :p1 a :Product ;
            rdfs:label "Super Widget" ;
            :price 19.99 .
        """
        parser2 = OWLParser(instance_ttl.encode("utf-8"))
        schema_triples, instance_triples = parser2.classify_triples()
        await importer.import_instances(schema_triples, instance_triples)

        # Search for p1
        results = await storage.search_instances(search_term="p1")
        print(f"\nSearch results for p1: {results}")
        assert len(results) > 0
        p1 = results[0]
        print(f"p1 aliases: {p1['aliases']}")
        assert "Super Widget" in p1["aliases"]

        print("\nAll verifications passed!")


if __name__ == "__main__":
    asyncio.run(test_ontology_features())
