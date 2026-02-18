# backend/app/services/pg_graph_storage.py
"""
PostgreSQL 图存储服务

使用 PostgreSQL + SQL/PGQ 实现图数据存储和查询。

主要功能：
1. Schema 层操作：类定义、关系定义
2. Instance 层操作：实体查询、关系遍历、路径查找
3. 统计查询：节点统计、关系统计
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select,
    update,
    delete,
    func,
    and_,
    or_,
    text,
    insert,
    literal_column,
    case,
)
from sqlalchemy.orm import selectinload
from app.models.graph import (
    GraphEntity,
    GraphRelationship,
    SchemaClass,
    SchemaRelationship,
)

logger = logging.getLogger(__name__)


class PGGraphStorage:
    """PostgreSQL 图存储服务

    提供与原 GraphTools 兼容的接口，方便迁移。
    """

    def __init__(self, db: AsyncSession, event_emitter: Any = None):
        self.db = db
        self.event_emitter = event_emitter

    # ==================== Event Emission ====================

    async def _emit_update_event(
        self,
        entity_type: str,
        entity_id: str,
        property: str,
        old_value: Any,
        new_value: Any,
        actor_name: str | None = None,
        actor_type: str | None = None,
    ) -> None:
        """触发更新事件"""
        if self.event_emitter is None:
            logger.warning(
                f"No event_emitter configured, skipping event for {entity_type}.{property}"
            )
            return

        from app.rule_engine.models import UpdateEvent

        event = UpdateEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            property=property,
            old_value=old_value,
            new_value=new_value,
            actor_name=actor_name,
            actor_type=actor_type,
        )
        logger.warning(
            f"Emitting UpdateEvent: {entity_type}.{property} on {entity_id} ({old_value} -> {new_value}) by {actor_name}({actor_type})"
        )
        self.event_emitter.emit(event)

    async def _emit_graph_view_event(
        self, nodes: List[Dict], edges: List[Dict]
    ) -> None:
        """触发图谱预览事件"""
        if self.event_emitter is None:
            return

        from app.rule_engine.models import GraphViewEvent

        event = GraphViewEvent(nodes=nodes, edges=edges)
        self.event_emitter.emit(event)

    # ==================== 基础操作 ====================

    async def clear_graph(self, clear_ontology: bool = True):
        """清除图谱数据

        Args:
            clear_ontology: 是否同时清除本体定义（SchemaClass/SchemaRelationship）
        """
        # 先清除实例数据
        await self.db.execute(delete(GraphRelationship))
        await self.db.execute(
            delete(GraphEntity).where(GraphEntity.is_instance == True)
        )

        # 如果需要，清除本体数据
        if clear_ontology:
            await self.db.execute(delete(SchemaRelationship))
            await self.db.execute(delete(SchemaClass))
            # 同时清除所有 GraphEntity，包括那些作为 Schema 定义的（如果有的话）
            await self.db.execute(delete(GraphEntity))

        await self.db.commit()

    async def get_entity_by_id(self, entity_id: int) -> Optional[Dict]:
        """根据数据库 ID 获取实体详情"""
        result = await self.db.execute(
            select(GraphEntity).where(
                GraphEntity.id == entity_id, GraphEntity.is_instance == True
            )
        )
        entity = result.scalar_one_or_none()

        if not entity:
            return None

        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "properties": {
                k: v
                for k, v in (entity.properties or {}).items()
                if not k.startswith("__")
            },
            "aliases": (entity.properties or {}).get("__aliases__", []),
        }

    async def update_entity(
        self,
        entity_type: str,
        entity_id: str,
        updates: Dict[str, Any],
        actor_name: str | None = None,
        actor_type: str | None = None,
    ) -> Dict[str, Any]:
        """更新实体属性并触发事件"""
        # 尝试按 ID 或 name 查找
        query = select(GraphEntity).where(GraphEntity.entity_type == entity_type)
        if entity_id.isdigit():
            query = query.where(GraphEntity.id == int(entity_id))
        else:
            query = query.where(GraphEntity.name == entity_id)

        result = await self.db.execute(query)
        entity = result.scalar_one_or_none()

        if not entity:
            return {}

        old_values = (entity.properties or {}).copy()

        # 合并更新
        new_properties = {**old_values, **updates}

        await self.db.execute(
            update(GraphEntity)
            .where(
                GraphEntity.name == entity_id, GraphEntity.entity_type == entity_type
            )
            .values(properties=new_properties)
        )
        await self.db.commit()

        # 触发事件
        for key, new_val in updates.items():
            old_val = old_values.get(key)
            if old_val != new_val:
                await self._emit_update_event(
                    entity_type,
                    entity_id,
                    key,
                    old_val,
                    new_val,
                    actor_name=actor_name,
                    actor_type=actor_type,
                )

        return {**new_properties}

    # ==================== Schema 查询 ====================

    async def get_ontology_classes(self, accessible_entity_types: List[str] = None) -> List[Dict]:
        """获取所有类定义"""
        query = select(SchemaClass)

        # 添加实体类型过滤
        if accessible_entity_types is not None and accessible_entity_types:
            query = query.where(SchemaClass.name.in_(accessible_entity_types))

        result = await self.db.execute(query)
        classes = result.scalars().all()
        classes_data = [
            {
                "name": c.name,
                "label": (
                    c.label
                    if isinstance(c.label, list)
                    else ([c.label] if c.label else [])
                ),
                "dataProperties": c.data_properties or [],
                "color": c.color,
            }
            for c in classes
        ]

        # 触发图谱预览事件
        viz_nodes = [
            {
                "id": c["name"],
                "label": c["name"],
                "type": c["name"],  # 使用类名作为类型，方便着色
                "properties": {"attributes": c["dataProperties"]},
            }
            for c in classes_data
        ]
        if viz_nodes:
            await self._emit_graph_view_event(nodes=viz_nodes, edges=[])

        return classes_data

    async def get_ontology_relationships(self) -> List[Dict]:
        """获取所有关系定义"""
        result = await self.db.execute(
            select(
                SchemaClass.name.label("source_class"),
                SchemaRelationship.relationship_type.label("relationship"),
                SchemaClass.name.label("target_class"),
            ).join(
                SchemaRelationship, SchemaClass.id == SchemaRelationship.source_class_id
            )
        )
        # 需要更复杂的查询来同时获取 source 和 target
        result = await self.db.execute(
            select(SchemaRelationship)
            .options(selectinload(SchemaRelationship.source_class))
            .options(selectinload(SchemaRelationship.target_class))
        )
        rels = result.scalars().all()
        rels_data = [
            {
                "source": r.source_class.name,
                "type": r.relationship_type,
                "target": r.target_class.name,
            }
            for r in rels
        ]

        # 触发图谱预览事件
        viz_nodes_set = set()
        viz_edges = []
        for r in rels_data:
            viz_nodes_set.add(r["source"])
            viz_nodes_set.add(r["target"])
            viz_edges.append(
                {"source": r["source"], "target": r["target"], "label": r["type"]}
            )

        viz_nodes = [
            {"id": node_name, "label": node_name, "type": node_name, "properties": {}}
            for node_name in viz_nodes_set
        ]

        if viz_nodes:
            await self._emit_graph_view_event(nodes=viz_nodes, edges=viz_edges)

        return rels_data

    async def describe_class(self, class_name: str) -> Dict:
        """描述一个类的定义"""
        # 获取类信息
        result = await self.db.execute(
            select(SchemaClass).where(SchemaClass.name == class_name)
        )
        cls = result.scalar_one_or_none()

        if not cls:
            return {"error": f"Class '{class_name}' not found"}

        class_data = {
            "name": cls.name,
            "label": cls.label,
            "dataProperties": cls.data_properties or [],
        }

        # 获取该类的关系
        result = await self.db.execute(
            select(SchemaRelationship)
            .options(selectinload(SchemaRelationship.source_class))
            .options(selectinload(SchemaRelationship.target_class))
            .where(
                or_(
                    SchemaRelationship.source_class_id == cls.id,
                    SchemaRelationship.target_class_id == cls.id,
                )
            )
        )
        rels = result.scalars().all()
        relationships_data = []
        for r in rels:
            if r.source_class_id == cls.id:
                relationships_data.append(
                    {
                        "relationship": r.relationship_type,
                        "target_class": r.target_class.name,
                    }
                )
            else:
                relationships_data.append(
                    {
                        "relationship": r.relationship_type,
                        "source_class": r.source_class.name,
                    }
                )

        result_data = {"class": class_data, "relationships": relationships_data}

        # 触发图谱预览事件
        viz_nodes = [
            {
                "id": class_name,
                "label": class_name,
                "type": class_name,
                "properties": {"attributes": class_data["dataProperties"]},
            }
        ]
        viz_edges = []
        for r in relationships_data:
            target = r.get("target_class") or r.get("source_class")
            if target:
                viz_nodes.append(
                    {"id": target, "label": target, "type": target, "properties": {}}
                )
                source = class_name if "target_class" in r else target
                dest = target if "target_class" in r else class_name
                viz_edges.append(
                    {"source": source, "target": dest, "label": r["relationship"]}
                )

        await self._emit_graph_view_event(nodes=viz_nodes, edges=viz_edges)

        return result_data

    async def add_ontology_class(
        self,
        name: str,
        label: Optional[str] = None,
        data_properties: List[str] = None,
        color: Optional[str] = None,
    ) -> Dict:
        """添加本体类定义"""
        # 检查是否已存在
        result = await self.db.execute(
            select(SchemaClass).where(SchemaClass.name == name)
        )
        if result.scalar_one_or_none():
            return {"error": f"Class '{name}' already exists"}

        # 确保 label 是列表
        if isinstance(label, str):
            label_list = [label]
        elif isinstance(label, list):
            label_list = label
        else:
            label_list = [name]

        new_class = SchemaClass(
            name=name,
            label=label_list,
            data_properties=data_properties or [],
            color=color,
        )
        self.db.add(new_class)
        await self.db.commit()
        return {
            "name": name,
            "label": label,
            "data_properties": data_properties or [],
            "color": color,
        }

    async def update_ontology_class(
        self,
        name: str,
        label: Optional[str] = None,
        data_properties: List[str] = None,
        color: Optional[str] = None,
    ) -> Dict:
        """更新本体类定义"""
        result = await self.db.execute(
            select(SchemaClass).where(SchemaClass.name == name)
        )
        cls = result.scalar_one_or_none()
        if not cls:
            return {"error": f"Class '{name}' not found"}

        if label is not None:
            if isinstance(label, str):
                # 支持逗号分隔的别名
                cls.label = [l.strip() for l in label.split(",") if l.strip()]
            else:
                cls.label = label
        if data_properties is not None:
            cls.data_properties = data_properties
        if color is not None:
            cls.color = color

        await self.db.commit()
        return {
            "name": name,
            "label": cls.label,
            "data_properties": cls.data_properties,
            "color": cls.color,
        }

    async def delete_ontology_class(self, name: str) -> Dict:
        """删除本体类定义"""
        result = await self.db.execute(
            select(SchemaClass).where(SchemaClass.name == name)
        )
        cls = result.scalar_one_or_none()
        if not cls:
            return {"error": f"Class '{name}' not found"}

        # 删除相关的关系定义
        await self.db.execute(
            delete(SchemaRelationship).where(
                or_(
                    SchemaRelationship.source_class_id == cls.id,
                    SchemaRelationship.target_class_id == cls.id,
                )
            )
        )

        await self.db.delete(cls)
        await self.db.commit()
        return {"message": f"Class '{name}' and its relationships deleted"}

    async def add_ontology_relationship(
        self, source: str, relationship_type: str, target: str
    ) -> Dict:
        """添加本体关系定义"""
        # 获取 IDs
        source_res = await self.db.execute(
            select(SchemaClass.id).where(SchemaClass.name == source)
        )
        source_id = source_res.scalar_one_or_none()

        target_res = await self.db.execute(
            select(SchemaClass.id).where(SchemaClass.name == target)
        )
        target_id = target_res.scalar_one_or_none()

        if not source_id or not target_id:
            return {"error": "Source or target class not found"}

        # 检查是否已存在
        existing = await self.db.execute(
            select(SchemaRelationship).where(
                SchemaRelationship.source_class_id == source_id,
                SchemaRelationship.target_class_id == target_id,
                SchemaRelationship.relationship_type == relationship_type,
            )
        )
        if existing.scalar_one_or_none():
            return {"error": "Relationship definition already exists"}

        new_rel = SchemaRelationship(
            source_class_id=source_id,
            target_class_id=target_id,
            relationship_type=relationship_type,
        )
        self.db.add(new_rel)
        await self.db.commit()
        return {"source": source, "type": relationship_type, "target": target}

    async def delete_ontology_relationship(
        self, source: str, relationship_type: str, target: str
    ) -> Dict:
        """删除本体关系定义"""
        source_res = await self.db.execute(
            select(SchemaClass.id).where(SchemaClass.name == source)
        )
        source_id = source_res.scalar_one_or_none()

        target_res = await self.db.execute(
            select(SchemaClass.id).where(SchemaClass.name == target)
        )
        target_id = target_res.scalar_one_or_none()

        if source_id and target_id:
            result = await self.db.execute(
                delete(SchemaRelationship).where(
                    SchemaRelationship.source_class_id == source_id,
                    SchemaRelationship.target_class_id == target_id,
                    SchemaRelationship.relationship_type == relationship_type,
                )
            )
            await self.db.commit()
            return {"message": "Relationship definition deleted"}

        return {"error": "Source or target class not found"}

    # ==================== Instance 查询 ====================

    async def search_instances(
        self, search_term: str, class_name: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """根据名称搜索实例节点"""
        from sqlalchemy import or_

        # 搜索名称或别名
        # 因为 properties['__aliases__'] 是 JSONB 数组，我们检查是否包含该词或数组元素匹配
        query = select(GraphEntity).where(
            or_(
                GraphEntity.name.ilike(f"%{search_term}%"),
                # PostgreSQL JSONB 搜索：由于 ILIKE 很难直接应用于数组元素，这里我们使用通用 SQL
                text(
                    "id IN (SELECT id FROM graph_entities, jsonb_array_elements_text(properties->'__aliases__') as a WHERE a ILIKE :term)"
                ),
            ),
            GraphEntity.is_instance == True,
        )

        if class_name:
            query = query.where(GraphEntity.entity_type == class_name)

        query = query.limit(limit)
        result = await self.db.execute(query, {"term": f"%{search_term}%"})
        entities = result.scalars().all()

        results = [
            {
                "id": e.id,
                "name": e.name,
                "labels": [e.entity_type],
                "aliases": (e.properties or {}).get("__aliases__", []),
                "properties": {
                    k: v
                    for k, v in (e.properties or {}).items()
                    if not k.startswith("__")
                },
            }
            for e in entities
        ]

        # 触发可视化事件
        nodes = []
        for r in results:
            nodes.append(
                {
                    "id": r["name"],
                    "label": r["name"],
                    "source_id": r.get("source_id"),
                    "aliases": r["aliases"],
                    "type": r["labels"][0] if r["labels"] else "Entity",
                    "properties": r["properties"],
                }
            )

        if nodes:
            await self._emit_graph_view_event(nodes=nodes, edges=[])

        return results

    async def get_instance_neighbors(
        self,
        instance_name: str,
        hops: int = 1,
        direction: str = "both",
        entity_type: Optional[str] = None,
        property_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """查询实例节点的邻居

        使用递归 CTE 实现多跳邻居查询。
        """
        if direction == "outgoing":
            direction_filter = "direction = 1"  # 仅出边
        elif direction == "incoming":
            direction_filter = "direction = -1"  # 仅入边
        else:
            direction_filter = "direction IN (1, -1)"  # 双向

        # 使用递归 CTE 查询邻居
        # 注意：这里的 CTE 只是为了说明逻辑，实际执行使用的是 _get_one_hop_neighbors 或 _get_multi_hop_neighbors
        # 即使更新了这里的文档字符串，核心逻辑还是在下面两个方法中

        # 由于参数化 CTE 比较复杂，这里使用简化的实现
        # 对于 1 跳查询，直接使用 JOIN
        if hops == 1:
            return await self._get_one_hop_neighbors(
                instance_name, direction, entity_type, property_filter
            )

        # 对于多跳查询，使用构建的方式
        return await self._get_multi_hop_neighbors(
            instance_name, hops, direction, entity_type, property_filter
        )

    async def _get_one_hop_neighbors(
        self,
        instance_name: str,
        direction: str,
        entity_type: Optional[str] = None,
        property_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """获取 1 跳邻居（简化实现）"""
        # 先获取起始节点
        # 先获取起始节点
        result = await self.db.execute(
            select(GraphEntity).where(
                GraphEntity.name == instance_name, GraphEntity.is_instance == True
            )
        )
        start_entity = result.scalar_one_or_none()
        if not start_entity:
            return []

        start_node = start_entity.id

        # 根据方向查询关系
        if direction == "outgoing":
            query = (
                select(GraphRelationship, GraphEntity)
                .join(GraphEntity, GraphEntity.id == GraphRelationship.target_id)
                .where(GraphRelationship.source_id == start_node)
            )

            if entity_type:
                query = query.where(GraphEntity.entity_type == entity_type)

            if property_filter:
                for key, value in property_filter.items():
                    query = query.where(
                        GraphEntity.properties[key].astext == str(value)
                    )

        elif direction == "incoming":
            query = (
                select(GraphRelationship, GraphEntity)
                .join(GraphEntity, GraphEntity.id == GraphRelationship.source_id)
                .where(GraphRelationship.target_id == start_node)
            )

            if entity_type:
                query = query.where(GraphEntity.entity_type == entity_type)

            if property_filter:
                for key, value in property_filter.items():
                    query = query.where(
                        GraphEntity.properties[key].astext == str(value)
                    )

        else:  # both
            # 查询所有关联的关系和实体
            query = select(GraphRelationship).where(
                or_(
                    GraphRelationship.source_id == start_node,
                    GraphRelationship.target_id == start_node,
                )
            )

        rel_result = await self.db.execute(query)
        neighbors = []
        if direction in ["outgoing", "incoming"]:
            for row in rel_result.all():
                rel, entity = row
                neighbors.append(
                    {
                        "id": entity.id,
                        "name": entity.name,
                        "labels": [entity.entity_type],
                        "properties": {
                            k: v
                            for k, v in (entity.properties or {}).items()
                            if not k.startswith("__")
                        },
                        "relationships": [
                            {
                                "id": rel.id,
                                "type": rel.relationship_type,
                                "source": (
                                    instance_name
                                    if direction == "outgoing"
                                    else entity.name
                                ),
                                "target": (
                                    entity.name
                                    if direction == "outgoing"
                                    else instance_name
                                ),
                            }
                        ],
                    }
                )
        else:  # both
            rels = rel_result.scalars().all()
            neighbor_ids = set()
            for rel in rels:
                if rel.source_id == start_node:
                    neighbor_ids.add(rel.target_id)
                else:
                    neighbor_ids.add(rel.source_id)

            if not neighbor_ids:
                return []

            query = select(GraphEntity).where(GraphEntity.id.in_(neighbor_ids))
            if entity_type:
                query = query.where(GraphEntity.entity_type == entity_type)
            if property_filter:
                for key, value in property_filter.items():
                    query = query.where(
                        GraphEntity.properties[key].astext == str(value)
                    )

            entities_result = await self.db.execute(query)
            entities = {e.id: e for e in entities_result.scalars().all()}

            for rel in rels:
                neighbor_id = (
                    rel.target_id if rel.source_id == start_node else rel.source_id
                )
                entity = entities.get(neighbor_id)
                if entity:
                    neighbors.append(
                        {
                            "id": entity.id,
                            "name": entity.name,
                            "labels": [entity.entity_type],
                            "properties": {
                                k: v
                                for k, v in (entity.properties or {}).items()
                                if not k.startswith("__")
                            },
                            "relationships": [
                                {
                                    "id": rel.id,
                                    "type": rel.relationship_type,
                                    "source": (
                                        instance_name
                                        if rel.source_id == start_node
                                        else entity.name
                                    ),
                                    "target": (
                                        entity.name
                                        if rel.source_id == start_node
                                        else instance_name
                                    ),
                                }
                            ],
                        }
                    )

        # 触发可视化事件
        viz_nodes = []
        viz_edges = []

        # 起始节点
        viz_nodes.append(
            {
                "id": instance_name,
                "label": instance_name,
                "type": start_entity.entity_type,
                "properties": {
                    k: v
                    for k, v in (start_entity.properties or {}).items()
                    if not k.startswith("__")
                },
            }
        )

        for n in neighbors:
            viz_nodes.append(
                {
                    "id": n["name"],
                    "label": n["name"],
                    "type": n["labels"][0] if n["labels"] else "Entity",
                    "properties": n["properties"],
                }
            )
            for r in n["relationships"]:
                viz_edges.append(
                    {
                        "source": r["source"],
                        "target": r["target"],
                        "label": r["type"],
                    }
                )

        if viz_nodes:
            await self._emit_graph_view_event(nodes=viz_nodes, edges=viz_edges)

        return neighbors

    async def _get_multi_hop_neighbors(
        self,
        instance_name: str,
        hops: int,
        direction: str,
        entity_type: Optional[str] = None,
        property_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """获取多跳邻居（使用 SQL 原生查询）"""
        # 获取起始节点 ID
        result = await self.db.execute(
            select(GraphEntity).where(
                GraphEntity.name == instance_name, GraphEntity.is_instance == True
            )
        )
        start_entity = result.scalar_one_or_none()
        if not start_entity:
            return []

        start_id = start_entity.id

        # 构建方向过滤条件
        if direction == "outgoing":
            direction_clause = "r.source_id = ns.id"
        elif direction == "incoming":
            direction_clause = "r.target_id = ns.id"
        else:  # both
            direction_clause = "(r.source_id = ns.id OR r.target_id = ns.id)"

        # 构建过滤器条件
        filter_conditions = []
        filter_params = {}

        # 构建过滤器条件 (用于最终结果过滤)
        filter_conditions = []
        filter_params = {}

        if entity_type:
            filter_conditions.append("entity_type = :entity_type")
            filter_params["entity_type"] = entity_type

        if property_filter:
            for key, value in property_filter.items():
                param_key = f"prop_{key}"
                filter_conditions.append(f"properties->>'{key}' = :{param_key}")
                filter_params[param_key] = str(value)

        filter_clause = " AND ".join(filter_conditions)
        if filter_clause:
            filter_clause = f"AND {filter_clause}"

        sql_query = text(
            f"""
        WITH RECURSIVE neighbor_search AS (
            -- 基础：起始节点
            SELECT
                e.id,
                e.name,
                e.entity_type,
                e.properties,
                1 as depth,
                ARRAY[e.id] as path_ids,
                NULL::varchar as rel_type,
                NULL::varchar as source_name
            FROM graph_entities e
            WHERE e.id = :start_id AND e.is_instance = true

            UNION ALL

            -- 递归：查找邻居
            SELECT
                CASE WHEN r.source_id = ns.id THEN r.target_id ELSE r.source_id END as id,
                CASE WHEN r.source_id = ns.id THEN t.name ELSE s.name END as name,
                CASE WHEN r.source_id = ns.id THEN t.entity_type ELSE s.entity_type END as entity_type,
                CASE WHEN r.source_id = ns.id THEN t.properties ELSE s.properties END as properties,
                ns.depth + 1 as depth,
                ns.path_ids || CASE WHEN r.source_id = ns.id THEN r.target_id ELSE r.source_id END as path_ids,
                r.relationship_type as rel_type,
                ns.name as source_name
            FROM neighbor_search ns
            JOIN graph_relationships r ON {direction_clause}
            JOIN graph_entities s ON r.source_id = s.id
            JOIN graph_entities t ON r.target_id = t.id
            WHERE ns.depth <= :hops
            AND NOT (CASE WHEN r.source_id = ns.id THEN r.target_id ELSE r.source_id END = ANY(ns.path_ids))
        )
        SELECT id, name, entity_type, properties, rel_type, source_name, depth
        FROM neighbor_search
        ORDER BY depth ASC
        LIMIT 500
        """
        )

        params = {"start_id": start_id, "hops": hops, **filter_params}
        result = await self.db.execute(sql_query, params)
        rows = result.fetchall()

        # 全部节点和边，用于可视化 (去重 ID)
        all_nodes = {}
        all_edges = []

        # 匹配过滤器的结果
        filtered_results = []
        seen_filtered_ids = set()

        for row in rows:
            node_id, name, etype, props, rel_type, source_name, depth = row

            # 添加到全量节点（用于可视化）
            if node_id not in all_nodes:
                all_nodes[node_id] = {
                    "id": name,
                    "label": name,
                    "type": etype,
                    "properties": {
                        k: v for k, v in (props or {}).items() if not k.startswith("__")
                    },
                }

            # 添加边（用于可视化）
            if rel_type and source_name:
                all_edges.append(
                    {"source": source_name, "target": name, "label": rel_type}
                )

            # 检查是否满足过滤器条件并行成结果
            if depth > 1:
                match = True
                if entity_type and etype != entity_type:
                    match = False
                if match and property_filter:
                    for k, v in property_filter.items():
                        if props.get(k) != str(v):
                            match = False
                            break

                if match and node_id not in seen_filtered_ids:
                    filtered_results.append(
                        {
                            "id": node_id,
                            "name": name,
                            "labels": [etype],
                            "properties": all_nodes[node_id]["properties"],
                            "aliases": (props or {}).get("__aliases__", []),
                            "distance": depth - 1,
                            "relationships": (
                                [
                                    {
                                        "type": rel_type,
                                        "source": source_name,
                                        "target": name,
                                    }
                                ]
                                if rel_type
                                else []
                            ),
                        }
                    )
                    seen_filtered_ids.add(node_id)

        # 触发可视化事件
        viz_nodes = list(all_nodes.values())
        viz_edges = all_edges

        if viz_nodes:
            await self._emit_graph_view_event(nodes=viz_nodes, edges=viz_edges)

        return filtered_results[:100]

    async def find_path_between_instances(
        self,
        start_name: str,
        end_name: str,
        max_depth: int = 5,
    ) -> Optional[Dict]:
        """查找两个实例之间的最短路径

        使用递归 CTE 实现 BFS 最短路径查找。
        """
        # 获取起点和终点节点
        result = await self.db.execute(
            select(GraphEntity.id, GraphEntity.name, GraphEntity.entity_type).where(
                GraphEntity.name == start_name, GraphEntity.is_instance == True
            )
        )
        start = result.one_or_none()
        if not start:
            return None

        result = await self.db.execute(
            select(GraphEntity.id, GraphEntity.name, GraphEntity.entity_type).where(
                GraphEntity.name == end_name, GraphEntity.is_instance == True
            )
        )
        end = result.one_or_none()
        if not end:
            return None

        # 使用 BFS 递归 CTE 查找最短路径
        path_query = text(
            """
        WITH RECURSIVE shortest_path AS (
            -- 起点
            SELECT
                s.id as current_id,
                s.name as current_name,
                s.entity_type as current_type,
                ARRAY[s.id] as path_ids,
                ARRAY[s.name] as path_names,
                ARRAY[s.entity_type] as path_labels,
                ARRAY[]::text[] as rel_types,
                0 as depth
            FROM graph_entities s
            WHERE s.id = :start_id

            UNION ALL

            -- 扩展路径
            SELECT
                CASE
                    WHEN r.source_id = sp.current_id THEN r.target_id
                    ELSE r.source_id
                END as current_id,
                CASE
                    WHEN r.source_id = sp.current_id THEN t.name
                    ELSE s.name
                END as current_name,
                CASE
                    WHEN r.source_id = sp.current_id THEN t.entity_type
                    ELSE s.entity_type
                END as current_type,
                sp.path_ids || CASE
                    WHEN r.source_id = sp.current_id THEN r.target_id
                    ELSE r.source_id
                END as path_ids,
                sp.path_names || CASE
                    WHEN r.source_id = sp.current_id THEN t.name
                    ELSE s.name
                END as path_names,
                sp.path_labels || CASE
                    WHEN r.source_id = sp.current_id THEN t.entity_type
                    ELSE s.entity_type
                END as path_labels,
                sp.rel_types || r.relationship_type as rel_types,
                sp.depth + 1 as depth
            FROM shortest_path sp
            JOIN graph_relationships r ON (r.source_id = sp.current_id OR r.target_id = sp.current_id)
            JOIN graph_entities s ON r.source_id = s.id
            JOIN graph_entities t ON r.target_id = t.id
            WHERE sp.depth < :max_depth
            AND NOT (CASE WHEN r.source_id = sp.current_id THEN r.target_id ELSE r.source_id END = ANY(sp.path_ids))
        )
        SELECT path_names, path_labels, rel_types, path_ids
        FROM shortest_path
        WHERE path_names[array_length(path_names, 1)] = :end_name
        ORDER BY array_length(path_names, 1) ASC
        LIMIT 1
        """
        )

        result = await self.db.execute(
            path_query,
            {"start_id": start[0], "end_name": end_name, "max_depth": max_depth},
        )
        row = result.first()

        if not row:
            return None

        path_names, path_labels, rel_types, path_ids = row

        # 构建节点列表
        nodes = [
            {"id": node_id, "name": name, "labels": [label]}
            for node_id, name, label in zip(path_ids, path_names, path_labels)
        ]

        # 构建关系列表
        relationships = []
        for i, rel_type in enumerate(rel_types):
            relationships.append(
                {"type": rel_type, "source": path_names[i], "target": path_names[i + 1]}
            )

        # 触发可视化事件
        viz_nodes = []
        for n in nodes:
            viz_nodes.append(
                {
                    "id": n["name"],
                    "label": n["name"],
                    "type": n["labels"][0] if n["labels"] else "Entity",
                    "properties": {},  # 路径查询结果中没有属性，这里简化
                }
            )

        if viz_nodes:
            await self._emit_graph_view_event(nodes=viz_nodes, edges=relationships)

        return {"nodes": nodes, "relationships": relationships}

    async def get_instances_by_class(
        self, class_name: str, filters: Optional[Dict[str, Any]] = None, limit: int = 20
    ) -> List[Dict]:
        """获取某个类的所有实例"""
        query = select(GraphEntity).where(
            GraphEntity.entity_type == class_name, GraphEntity.is_instance == True
        )

        # 应用过滤条件（JSONB 属性查询）
        if filters:
            for key, value in filters.items():
                # 使用 JSONB 操作符查询属性
                query = query.where(GraphEntity.properties[key].astext == str(value))

        query = query.limit(limit)
        result = await self.db.execute(query)
        entities = result.scalars().all()

        results = [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "properties": {
                    k: v
                    for k, v in (e.properties or {}).items()
                    if not k.startswith("__")
                },
                "aliases": (e.properties or {}).get("__aliases__", []),
            }
            for e in entities
        ]

        # 触发可视化事件
        nodes = []
        for r in results:
            nodes.append(
                {
                    "id": r["name"],
                    "label": r["name"],
                    "type": class_name,
                    "properties": r["properties"],
                }
            )

        if nodes:
            await self._emit_graph_view_event(nodes=nodes, edges=[])

        return results

    async def get_entity_by_name(
        self, name: str, entity_type: Optional[str] = None
    ) -> Optional[Dict]:
        """根据名称获取实体详情"""
        query = select(GraphEntity).where(
            GraphEntity.name == name, GraphEntity.is_instance == True
        )
        if entity_type:
            query = query.where(GraphEntity.entity_type == entity_type)

        result = await self.db.execute(query)
        entity = result.scalar_one_or_none()

        if not entity:
            return None

        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "properties": {
                k: v
                for k, v in (entity.properties or {}).items()
                if not k.startswith("__")
            },
            "aliases": (entity.properties or {}).get("__aliases__", []),
        }

    # ==================== 统计查询 ====================

    async def get_node_statistics(self, node_label: Optional[str] = None) -> Dict:
        """获取节点统计信息"""
        if node_label:
            # 按类型统计
            result = await self.db.execute(
                select(func.count(GraphEntity.id)).where(
                    GraphEntity.entity_type == node_label,
                    GraphEntity.is_instance == True,
                )
            )
            total_count = result.scalar() or 0

            # 获取样本名称
            result = await self.db.execute(
                select(GraphEntity.name)
                .where(
                    GraphEntity.entity_type == node_label,
                    GraphEntity.is_instance == True,
                )
                .limit(5)
            )
            sample_names = [row[0] for row in result.all()]

            return {"total_count": total_count, "sample_names": sample_names}
        else:
            # 按类型分布统计
            result = await self.db.execute(
                select(
                    GraphEntity.entity_type, func.count(GraphEntity.id).label("count")
                )
                .where(GraphEntity.is_instance == True)
                .group_by(GraphEntity.entity_type)
                .order_by(func.count(GraphEntity.id).desc())
                .limit(20)
            )
            distribution = [
                {"labels": [row[0]], "count": row[1]} for row in result.all()
            ]
            return {"label_distribution": distribution}

    async def get_relationship_statistics(self) -> List[Dict]:
        """获取关系类型统计"""
        result = await self.db.execute(
            select(
                GraphRelationship.relationship_type,
                func.count(GraphRelationship.id).label("count"),
            )
            .group_by(GraphRelationship.relationship_type)
            .order_by(func.count(GraphRelationship.id).desc())
            .limit(50)
        )

        return [{"relationship_type": row[0], "count": row[1]} for row in result.all()]

    async def get_graph_statistics(self) -> Dict:
        """获取图的整体统计信息"""
        # 节点总数
        node_count = await self.db.execute(
            select(func.count(GraphEntity.id)).where(GraphEntity.is_instance == True)
        )
        node_count = node_count.scalar() or 0

        # 关系总数
        rel_count = await self.db.execute(select(func.count(GraphRelationship.id)))
        rel_count = rel_count.scalar() or 0

        # 类定义数
        class_count = await self.db.execute(select(func.count(SchemaClass.id)))
        class_count = class_count.scalar() or 0

        # 类关系定义数
        schema_rel_count = await self.db.execute(
            select(func.count(SchemaRelationship.id))
        )
        schema_rel_count = schema_rel_count.scalar() or 0

        return {
            "total_nodes": node_count,
            "total_relationships": rel_count,
            "total_classes": class_count,
            "total_schema_relationships": schema_rel_count,
        }

    async def get_random_graph(self, limit: int = 100, accessible_entity_types: List[str] = None) -> Dict[str, List[Dict]]:
        """获取随机的实例图谱片段（节点 + 关系）"""
        # 1. 随机获取一些节点
        query = (
            select(GraphEntity)
            .where(GraphEntity.is_instance == True)
        )

        # 添加实体类型过滤
        if accessible_entity_types is not None and accessible_entity_types:
            query = query.where(GraphEntity.type.in_(accessible_entity_types))

        query = query.order_by(func.random()).limit(limit)
        result = await self.db.execute(query)
        entities = result.scalars().all()

        if not entities:
            return {"nodes": [], "relationships": []}

        entity_ids = [e.id for e in entities]
        entity_map = {e.id: e for e in entities}

        # 2. 获取这些节点之间的关系
        rel_query = select(GraphRelationship).where(
            and_(
                GraphRelationship.source_id.in_(entity_ids),
                GraphRelationship.target_id.in_(entity_ids),
            )
        )
        rel_result = await self.db.execute(rel_query)
        relationships = rel_result.scalars().all()

        # 3. 组装结果
        nodes_data = [
            {
                "id": e.id,
                "name": e.name,
                "label": e.name,
                "nodeLabel": e.entity_type,
                "labels": [e.entity_type],
                "properties": {
                    k: v
                    for k, v in (e.properties or {}).items()
                    if not k.startswith("__")
                },
            }
            for e in entities
        ]

        rels_data = [
            {
                "id": r.id,
                "source": r.source_id,
                "target": r.target_id,
                "type": r.relationship_type,
            }
            for r in relationships
        ]

        return {"nodes": nodes_data, "relationships": rels_data}
