# backend/app/models/graph.py
"""
PostgreSQL 图存储模型

使用关系型数据库存储图数据（节点和关系）。
设计支持 SQL/PGQ (Property Graph Queries) 标准。

数据模型说明：
- GraphEntity: 存储图中的实体节点
- GraphRelationship: 存储实体间的关系边
- SchemaClass: 存储本体层（Ontology）的类定义
- SchemaRelationship: 存储本体层类之间的关系定义
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, DateTime, Index, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GraphEntity(Base):
    """图实体节点表

    对应 Neo4j 的节点 (Node)。
    存储所有实例数据和属性。
    """
    __tablename__ = "graph_entities"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(255), nullable=False)  # 对应 Neo4j 的 Label
    is_instance = Column(Boolean, default=True, index=True)  # True=实例数据, False=Schema节点
    properties = Column(JSON, default=dict)  # 动态属性，JSONB 格式
    uri = Column(String(1000))  # 原始 RDF URI（可选，用于追溯）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系映射
    # outgoing_relationships: 该实体作为源的所有关系
    # incoming_relationships: 该实体作为目标的所有关系
    outgoing_relationships = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.source_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.target_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index('idx_entities_name', 'name'),
        Index('idx_entities_type', 'entity_type'),
        Index('idx_entities_is_instance', 'is_instance'),
        Index('idx_entities_type_instance', 'entity_type', 'is_instance'),
    )


class GraphRelationship(Base):
    """图关系边表

    对应 Neo4j 的关系 (Relationship)。
    存储实体之间的有向关系。
    """
    __tablename__ = "graph_relationships"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    source_id = Column(Integer, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(255), nullable=False)  # 关系类型名称
    properties = Column(JSON, default=dict)  # 关系的属性（较少使用）
    created_at = Column(DateTime, server_default=func.now())

    # 实体映射
    source_entity = relationship(
        "GraphEntity",
        foreign_keys=[source_id],
        back_populates="outgoing_relationships",
    )
    target_entity = relationship(
        "GraphEntity",
        foreign_keys=[target_id],
        back_populates="incoming_relationships",
    )

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'relationship_type', name='uq_source_target_rel'),
        Index('idx_relationships_source', 'source_id'),
        Index('idx_relationships_target', 'target_id'),
        Index('idx_relationships_type', 'relationship_type'),
        Index('idx_relationships_source_target', 'source_id', 'target_id'),
        Index('idx_relationships_composite', 'source_id', 'relationship_type', 'target_id'),
    )


class SchemaClass(Base):
    """Schema 类定义表

    对应 Neo4j 的 Class:__Schema 节点。
    存储本体层（Ontology）的类定义。
    """
    __tablename__ = "schema_classes"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    name = Column(String(255), unique=True, nullable=False)
    label = Column(String(500))  # 人类可读的标签/描述
    data_properties = Column(JSON, default=list)  # 数据属性列表，如 ["name:string", "age:integer"]
    created_at = Column(DateTime, server_default=func.now())

    # Schema 级的关系定义
    source_schema_relationships = relationship(
        "SchemaRelationship",
        foreign_keys="SchemaRelationship.source_class_id",
        back_populates="source_class",
        cascade="all, delete-orphan",
    )
    target_schema_relationships = relationship(
        "SchemaRelationship",
        foreign_keys="SchemaRelationship.target_class_id",
        back_populates="target_class",
        cascade="all, delete-orphan",
    )


class SchemaRelationship(Base):
    """Schema 关系定义表

    对应 Neo4j 中 Schema 节点之间的关系。
    定义类之间允许的关系类型。
    """
    __tablename__ = "schema_relationships"

    id = Column(Integer, primary_key=True, autoincrement="auto")
    source_class_id = Column(Integer, ForeignKey("schema_classes.id", ondelete="CASCADE"), nullable=False)
    target_class_id = Column(Integer, ForeignKey("schema_classes.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    source_class = relationship(
        "SchemaClass",
        foreign_keys=[source_class_id],
        back_populates="source_schema_relationships",
    )
    target_class = relationship(
        "SchemaClass",
        foreign_keys=[target_class_id],
        back_populates="target_schema_relationships",
    )

    __table_args__ = (
        UniqueConstraint('source_class_id', 'target_class_id', 'relationship_type'),
    )
