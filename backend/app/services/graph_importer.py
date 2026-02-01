# backend/app/services/graph_importer.py
from typing import List, Set
from neo4j import AsyncSession
from app.services.owl_parser import OWLParser, Triple


class GraphImporter:
    """将 OWL 解析结果导入 Neo4j"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.object_property_uris: Set[str] = set()
        self.data_property_uris: Set[str] = set()

    async def import_schema(self, parser: OWLParser) -> dict:
        """导入 Schema 层

        - Class -> 创建 Class 节点
        - ObjectProperty -> 创建 Class 节点之间的关系（使用属性名作为关系类型）
        - DatatypeProperty -> 记录在 Class 节点上（作为可用属性列表）
        """
        classes = parser.extract_classes()
        properties = parser.extract_properties()

        stats = {"classes": 0, "properties": 0}

        # 记录属性类型，用于后续实例导入
        for prop in properties:
            if prop["type"] == "object":
                self.object_property_uris.add(prop["uri"])
            else:
                self.data_property_uris.add(prop["uri"])

        # 批量导入类节点（不存储 URI）
        if classes:
            await self.session.run(
                """
                UNWIND $classes AS cls
                MERGE (c:Class:__Schema {name: cls.name})
                SET c.label = cls.label
                """,
                classes=[{"name": c["name"], "label": c.get("label")} for c in classes],
            )
            stats["classes"] = len(classes)

        # ObjectProperty -> 创建 Class 之间的关系（使用属性名作为关系类型）
        object_props = [p for p in properties if p["type"] == "object"]
        for prop in object_props:
            if prop.get("domain") and prop.get("range"):
                domain_name = prop["domain"].split("#")[-1].split("/")[-1]
                range_name = prop["range"].split("#")[-1].split("/")[-1]
                rel_type = prop["name"]  # 直接使用属性名作为关系类型

                await self.session.run(
                    f"""
                    MATCH (domain:Class:__Schema {{name: $domain}})
                    MATCH (range:Class:__Schema {{name: $range}})
                    MERGE (domain)-[r:`{rel_type}`]->(range)
                    """,
                    domain=domain_name,
                    range=range_name,
                )
                stats["properties"] += 1

        # DatatypeProperty -> 添加到 Class 节点的属性列表
        data_props = [p for p in properties if p["type"] != "object"]
        for prop in data_props:
            if prop.get("domain"):
                domain_name = prop["domain"].split("#")[-1].split("/")[-1]
                range_type = prop.get("range", "string")
                if range_type:
                    range_type = range_type.split("#")[-1].split("/")[-1]

                await self.session.run(
                    """
                    MATCH (c:Class:__Schema {name: $domain})
                    SET c.dataProperties = coalesce(c.dataProperties, []) + $prop_info
                    """,
                    domain=domain_name,
                    prop_info=f"{prop['name']}:{range_type}",
                )
                stats["properties"] += 1

        await self._create_schema_indexes()
        return stats

    async def import_instances(
        self, schema_triples: List[Triple], instance_triples: List[Triple]
    ) -> dict:
        """导入 Instance 层

        - ObjectProperty 谓词 -> 创建关系
        - DatatypeProperty 谓词 -> 设置节点属性
        """
        stats = {"nodes": 0, "relationships": 0, "properties": 0}

        # 收集类型声明和数据属性
        type_map = {}  # {instance_uri: class_uri}
        node_properties = {}  # {instance_uri: {prop_name: value}}
        relationships = []  # [{subject, predicate, object}]

        for triple in instance_triples:
            pred = triple.predicate

            # 类型声明
            if pred.endswith("type") or pred.endswith("#type"):
                type_map[triple.subject] = triple.obj

            # ObjectProperty -> 关系
            elif pred in self.object_property_uris:
                relationships.append(
                    {"subject": triple.subject, "predicate": pred, "object": triple.obj}
                )

            # DatatypeProperty -> 节点属性
            elif pred in self.data_property_uris:
                if triple.subject not in node_properties:
                    node_properties[triple.subject] = {}
                prop_name = pred.split("#")[-1].split("/")[-1]
                node_properties[triple.subject][prop_name] = triple.obj

            # 未知谓词，假设是关系
            else:
                relationships.append(
                    {"subject": triple.subject, "predicate": pred, "object": triple.obj}
                )

        # 按类分组创建节点（不存储 URI，使用 name 作为唯一标识）
        nodes_by_class: dict[str, list] = {}
        for subject_uri, class_uri in type_map.items():
            class_name = class_uri.split("#")[-1].split("/")[-1]
            node_name = subject_uri.split("#")[-1].split("/")[-1]
            props = node_properties.get(subject_uri, {})

            if class_name not in nodes_by_class:
                nodes_by_class[class_name] = []
            nodes_by_class[class_name].append(
                {
                    "name": node_name,
                    "props": props,
                    "_uri": subject_uri,  # 临时保留用于关系匹配
                }
            )

        # URI 到 name 的映射（用于创建关系）
        uri_to_name = {}
        for subject_uri, class_uri in type_map.items():
            uri_to_name[subject_uri] = subject_uri.split("#")[-1].split("/")[-1]

        # 批量创建每个类的节点（包含属性）
        for class_name, nodes in nodes_by_class.items():
            for node in nodes:
                props_str = ", ".join([f"n.`{k}` = ${k}" for k in node["props"].keys()])
                set_clause = "SET n.__is_instance = true"
                if props_str:
                    set_clause += f", {props_str}"

                params = {"name": node["name"], **node["props"]}

                await self.session.run(
                    f"""
                    MERGE (n:`{class_name}` {{name: $name}})
                    {set_clause}
                    """,
                    **params,
                )
                stats["nodes"] += 1
                stats["properties"] += len(node["props"])

        # 按关系类型分组创建关系
        relationships_by_type: dict[str, list] = {}
        for rel in relationships:
            rel_name = rel["predicate"].split("#")[-1].split("/")[-1]
            subject_name = rel["subject"].split("#")[-1].split("/")[-1]
            object_name = rel["object"].split("#")[-1].split("/")[-1]

            if rel_name not in relationships_by_type:
                relationships_by_type[rel_name] = []
            relationships_by_type[rel_name].append(
                {"subject": subject_name, "object": object_name}
            )

        # 批量创建关系
        for rel_name, rels in relationships_by_type.items():
            await self.session.run(
                f"""
                UNWIND $rels AS rel
                MATCH (s {{name: rel.subject}})
                MATCH (o {{name: rel.object}})
                MERGE (s)-[r:`{rel_name}`]->(o)
                """,
                rels=rels,
            )
            stats["relationships"] += len(rels)

        return stats

    async def _create_schema_indexes(self):
        """创建 Schema 层索引"""
        indexes = [
            "CREATE INDEX schema_class_name IF NOT EXISTS FOR (c:__Schema) ON (c.name)",
        ]

        for idx in indexes:
            try:
                await self.session.run(idx)
            except Exception:
                pass  # 索引可能已存在
