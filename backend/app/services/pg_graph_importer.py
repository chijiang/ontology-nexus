# backend/app/services/pg_graph_importer.py
"""
PostgreSQL 图导入器

将 OWL/TTL 解析结果导入 PostgreSQL 图存储。
"""

import logging
from typing import List, Set, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.graph import (
    GraphEntity,
    GraphRelationship,
    SchemaClass,
    SchemaRelationship,
)
from app.services.owl_parser import OWLParser, Triple

logger = logging.getLogger(__name__)


class PGGraphImporter:
    """将 OWL/TTL 解析结果导入 PostgreSQL"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.object_property_uris: Set[str] = set()
        self.data_property_uris: Set[str] = set()

        # 缓存：class_name -> entity_id 映射，用于快速查找
        self._entity_cache: Dict[str, int] = {}

    async def clear_cache(self):
        """清除缓存"""
        self._entity_cache.clear()

    async def import_schema(self, parser: OWLParser) -> Dict:
        """导入 Schema 层

        - Class -> 创建 SchemaClass 记录
        - ObjectProperty -> 创建 SchemaRelationship 记录
        - DatatypeProperty -> 记录在 SchemaClass 的 data_properties 中

        Args:
            parser: OWLParser 实例

        Returns:
            统计信息字典
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

        # 批量导入类节点
        if classes:
            for cls in classes:
                # 使用 MERGE 语义：存在则更新，不存在则创建
                result = await self.db.execute(
                    select(SchemaClass).where(SchemaClass.name == cls["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.label = cls.get("label", [])
                    existing.data_properties = []
                else:
                    new_class = SchemaClass(
                        name=cls["name"], label=cls.get("label", []), data_properties=[]
                    )
                    self.db.add(new_class)
                stats["classes"] += 1

            await self.db.commit()

        # ObjectProperty -> 创建 SchemaRelationship
        object_props = [p for p in properties if p["type"] == "object"]
        for prop in object_props:
            if prop.get("domain") and prop.get("range"):
                domain_name = prop["domain"].split("#")[-1].split("/")[-1]
                range_name = prop["range"].split("#")[-1].split("/")[-1]
                rel_type = prop["name"]

                # 获取 class IDs
                domain_result = await self.db.execute(
                    select(SchemaClass.id).where(SchemaClass.name == domain_name)
                )
                domain_id = domain_result.scalar_one_or_none()

                range_result = await self.db.execute(
                    select(SchemaClass.id).where(SchemaClass.name == range_name)
                )
                range_id = range_result.scalar_one_or_none()

                if domain_id and range_id:
                    # 检查是否已存在
                    existing = await self.db.execute(
                        select(SchemaRelationship).where(
                            SchemaRelationship.source_class_id == domain_id,
                            SchemaRelationship.target_class_id == range_id,
                            SchemaRelationship.relationship_type == rel_type,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        schema_rel = SchemaRelationship(
                            source_class_id=domain_id,
                            target_class_id=range_id,
                            relationship_type=rel_type,
                        )
                        self.db.add(schema_rel)
                        stats["properties"] += 1

        # DatatypeProperty -> 添加到 SchemaClass 的 data_properties
        data_props = [p for p in properties if p["type"] != "object"]
        for prop in data_props:
            if prop.get("domain"):
                domain_name = prop["domain"].split("#")[-1].split("/")[-1]
                range_type = prop.get("range", "string")
                if range_type:
                    range_type = range_type.split("#")[-1].split("/")[-1]

                result = await self.db.execute(
                    select(SchemaClass).where(SchemaClass.name == domain_name)
                )
                schema_class = result.scalar_one_or_none()

                if schema_class:
                    prop_info = f"{prop['name']}:{range_type}"
                    if schema_class.data_properties is None:
                        schema_class.data_properties = []
                    if prop_info not in (schema_class.data_properties or []):
                        schema_class.data_properties = (
                            schema_class.data_properties or []
                        ) + [prop_info]
                        stats["properties"] += 1

        await self.db.commit()
        return stats

    async def import_instances(
        self, schema_triples: List[Triple], instance_triples: List[Triple]
    ) -> Dict:
        """导入 Instance 层

        - ObjectProperty 谓词 -> 创建关系
        - DatatypeProperty 谓词 -> 设置节点属性
        - rdf:type -> 设置实体类型

        Args:
            schema_triples: Schema 层的三元组（未使用）
            instance_triples: 实例层的三元组

        Returns:
            统计信息字典
        """
        stats = {"nodes": 0, "relationships": 0, "properties": 0}

        # 清除缓存
        await self.clear_cache()

        # 收集数据
        type_map: Dict[str, str] = {}  # {instance_uri: class_name}
        node_properties: Dict[str, Dict[str, Any]] = (
            {}
        )  # {instance_name: {prop: value}}
        relationships: List[Dict[str, str]] = []  # [{subject, predicate, object}]

        for triple in instance_triples:
            pred = triple.predicate

            # 类型声明 (rdf:type)
            if (
                pred.endswith("type")
                or pred.endswith("#type")
                or "type" in pred.split("/")[-1]
            ):
                class_name = triple.obj.split("#")[-1].split("/")[-1]
                type_map[triple.subject] = class_name

            # 别名 (rdfs:label)
            elif pred.endswith("label") or pred.endswith("#label"):
                subject_name = triple.subject.split("#")[-1].split("/")[-1]
                if subject_name not in node_properties:
                    node_properties[subject_name] = {}
                if "__aliases__" not in node_properties[subject_name]:
                    node_properties[subject_name]["__aliases__"] = []
                node_properties[subject_name]["__aliases__"].append(triple.obj)

            # ObjectProperty -> 关系
            elif pred in self.object_property_uris:
                relationships.append(
                    {"subject": triple.subject, "predicate": pred, "object": triple.obj}
                )

            # DatatypeProperty -> 节点属性
            elif pred in self.data_property_uris:
                subject_name = triple.subject.split("#")[-1].split("/")[-1]
                if subject_name not in node_properties:
                    node_properties[subject_name] = {}
                prop_name = pred.split("#")[-1].split("/")[-1]
                node_properties[subject_name][prop_name] = triple.obj

            # 未知谓词，根据目标判断是关系还是属性
            else:
                # 如果目标看起来是 URI（包含 # 或 /），则当作关系
                if "#" in triple.obj or "/" in triple.obj:
                    relationships.append(
                        {
                            "subject": triple.subject,
                            "predicate": pred,
                            "object": triple.obj,
                        }
                    )
                else:
                    # 否则当作属性
                    subject_name = triple.subject.split("#")[-1].split("/")[-1]
                    if subject_name not in node_properties:
                        node_properties[subject_name] = {}
                    prop_name = pred.split("#")[-1].split("/")[-1]
                    node_properties[subject_name][prop_name] = triple.obj

        # 按类分组创建节点
        nodes_by_class: Dict[str, List[Dict]] = {}
        for subject_uri, class_name in type_map.items():
            node_name = subject_uri.split("#")[-1].split("/")[-1]
            props = node_properties.get(node_name, {})

            if class_name not in nodes_by_class:
                nodes_by_class[class_name] = []
            nodes_by_class[class_name].append(
                {"name": node_name, "props": props, "uri": subject_uri}
            )
            stats["properties"] += len(props)

        # 批量创建节点
        for class_name, nodes in nodes_by_class.items():
            for node in nodes:
                # 检查是否已存在
                existing = await self.db.execute(
                    select(GraphEntity).where(
                        GraphEntity.name == node["name"],
                        GraphEntity.entity_type == class_name,
                    )
                )
                if not existing.scalar_one_or_none():
                    new_entity = GraphEntity(
                        name=node["name"],
                        entity_type=class_name,
                        is_instance=True,
                        properties=node["props"],
                        uri=node.get("uri"),
                    )
                    self.db.add(new_entity)
                    stats["nodes"] += 1

        await self.db.commit()

        # 重建缓存用于关系创建
        await self._build_entity_cache()

        # 批量创建关系
        for rel in relationships:
            rel_name = rel["predicate"].split("#")[-1].split("/")[-1]
            source_name = rel["subject"].split("#")[-1].split("/")[-1]
            target_name = rel["object"].split("#")[-1].split("/")[-1]

            source_id = self._entity_cache.get(source_name)
            target_id = self._entity_cache.get(target_name)

            if source_id and target_id:
                # 检查关系是否已存在
                existing = await self.db.execute(
                    select(GraphRelationship).where(
                        GraphRelationship.source_id == source_id,
                        GraphRelationship.target_id == target_id,
                        GraphRelationship.relationship_type == rel_name,
                    )
                )
                if not existing.scalar_one_or_none():
                    new_rel = GraphRelationship(
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel_name,
                    )
                    self.db.add(new_rel)
                    stats["relationships"] += 1

        await self.db.commit()
        return stats

    async def _build_entity_cache(self):
        """构建实体名称到 ID 的缓存"""
        result = await self.db.execute(
            select(GraphEntity.id, GraphEntity.name).where(
                GraphEntity.is_instance == True
            )
        )
        for row in result.all():
            self._entity_cache[row[1]] = row[0]

    async def import_all(
        self,
        parser: OWLParser,
        schema_triples: List[Triple],
        instance_triples: List[Triple],
    ) -> Dict:
        """导入所有数据（Schema + Instance）

        Args:
            parser: OWLParser 实例
            schema_triples: Schema 层三元组
            instance_triples: Instance 层三元组

        Returns:
            合并的统计信息
        """
        schema_stats = await self.import_schema(parser)
        instance_stats = await self.import_instances(schema_triples, instance_triples)

        return {
            "schema": schema_stats,
            "instances": instance_stats,
            "total": {
                "classes": schema_stats.get("classes", 0),
                "schema_properties": schema_stats.get("properties", 0),
                "nodes": instance_stats.get("nodes", 0),
                "relationships": instance_stats.get("relationships", 0),
                "instance_properties": instance_stats.get("properties", 0),
            },
        }

    async def clear_all_data(self):
        """清除所有图数据（保留 Schema）"""
        await self.db.execute(delete(GraphRelationship))
        await self.db.execute(delete(GraphEntity))
        await self.db.commit()

    async def clear_schema(self):
        """清除 Schema 定义"""
        await self.db.execute(delete(SchemaRelationship))
        await self.db.execute(delete(SchemaClass))
        await self.db.commit()
