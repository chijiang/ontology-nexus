# backend/app/services/schema_matcher.py
from typing import List, Tuple, Dict
import json
import jieba
from difflib import SequenceMatcher
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.security import decrypt_data
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig


class SchemaMatcher:
    """Schema 匹配器 - 结合 NLP 和 LLM

    Schema 分为两层:
    - Ontology (本体): Class 节点和它们之间的关系定义
    - Instance (实例): 实际的数据节点和关系
    """

    def __init__(self, neo4j_session, llm_config: dict, neo4j_config: dict):
        self.session = neo4j_session
        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0,
        )
        self.neo4j_config = neo4j_config
        self.classes = {}  # Ontology: 类定义
        self.relationships = {}  # Ontology: 关系定义 (ObjectProperty)
        self.data_properties = {}  # Ontology: 数据属性定义
        self._load_synonyms()

    async def initialize(self):
        """异步初始化"""
        await self._load_schema()

    def _load_synonyms(self):
        """加载同义词库"""
        try:
            with open("app/data/synonyms.json", "r", encoding="utf-8") as f:
                self.synonyms = json.load(f)
        except FileNotFoundError:
            self.synonyms = {}

    async def _load_schema(self):
        """从 Neo4j 加载 Schema (Ontology 层)"""
        # 加载所有类 (Class 节点)
        result = await self.session.run(
            """
            MATCH (c:Class:__Schema)
            RETURN c.name as name, c.label as label, c.dataProperties as dataProperties
        """
        )
        classes_data = await result.data()
        self.classes = {
            record["name"]: {
                "label": record.get("label"),
                "dataProperties": record.get("dataProperties", []),
            }
            for record in classes_data
        }

        # 加载关系定义 (Class 之间的关系)
        result = await self.session.run(
            """
            MATCH (c1:Class:__Schema)-[r]->(c2:Class:__Schema)
            RETURN c1.name as source, type(r) as type, c2.name as target
        """
        )
        rels_data = await result.data()
        for record in rels_data:
            rel_type = record["type"]
            if rel_type not in self.relationships:
                self.relationships[rel_type] = []
            self.relationships[rel_type].append(
                {"source": record["source"], "target": record["target"]}
            )

    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def _fuzzy_match(
        self, text: str, candidates: Dict, threshold: float = 0.6
    ) -> List[Tuple]:
        """模糊匹配"""
        matches = []
        for name, info in candidates.items():
            # 直接匹配
            if name.lower() in text.lower() or text.lower() in name.lower():
                matches.append((name, 1.0, "exact"))
                continue

            # 同义词匹配
            for syn in self.synonyms.get(name, []):
                if syn.lower() in text.lower():
                    matches.append((name, 0.95, "synonym"))
                    break
            else:
                # 相似度匹配
                ratio = SequenceMatcher(None, name.lower(), text.lower()).ratio()
                if ratio >= threshold:
                    matches.append((name, ratio, "fuzzy"))

        return sorted(matches, key=lambda x: -x[1])

    async def match_entities(self, query: str) -> dict:
        """匹配查询中的实体"""
        tokens = self._tokenize(query)
        entity_matches = {}

        # 对每个分词进行匹配
        for token in tokens:
            if len(token) < 2:  # 跳过太短的词
                continue

            class_matches = self._fuzzy_match(token, self.classes)
            rel_matches = self._fuzzy_match(token, self.relationships)

            if class_matches:
                entity_matches[f"class:{token}"] = {
                    "type": "class",
                    "matched": class_matches[0][0],
                    "confidence": class_matches[0][1],
                    "method": class_matches[0][2],
                }
            elif rel_matches:
                entity_matches[f"relationship:{token}"] = {
                    "type": "relationship",
                    "matched": rel_matches[0][0],
                    "confidence": rel_matches[0][1],
                    "method": rel_matches[0][2],
                }

        # LLM 增强匹配
        llm_matches = await self._llm_match(query)

        return {"entities": entity_matches, "llm_entities": llm_matches}

    async def _llm_match(self, query: str) -> dict:
        """使用 LLM 进行语义匹配"""
        schema_context = self._build_schema_context()

        prompt = ChatPromptTemplate.from_template(
            """
你是一个知识图谱专家。请分析用户查询并识别相关的概念。

## Ontology (本体定义)
类 (Class):
{classes}

关系类型 (Relationships):
{relationships}

## 用户查询
{query}

请分析查询并返回 JSON 格式：
{{
    "detected_classes": ["类名1", "类名2"],
    "detected_relationships": ["关系名1"],
    "detected_instance_names": ["提到的具体实例名称，如订单号、人名等"],
    "query_intent": "ontology|instance|both",
    "query_type": "path|neighbors|search|statistics|describe",
    "confidence": "high|medium|low"
}}

说明：
- query_intent: 用户想查询的是 ontology (类和关系定义) 还是 instance (具体数据)
- detected_instance_names: 查询中提到的具体实例名称（如 PO_2024_001）
"""
        )

        chain = prompt | self.llm
        result = await chain.ainvoke(
            {
                "classes": json.dumps(list(self.classes.keys()), ensure_ascii=False),
                "relationships": json.dumps(
                    list(self.relationships.keys()), ensure_ascii=False
                ),
                "query": query,
            }
        )

        try:
            return json.loads(result.content)
        except:
            return {}

    def _build_schema_context(self) -> str:
        """构建 Schema 上下文描述"""
        lines = ["## Classes (类定义):"]
        for name, info in self.classes.items():
            props = info.get("dataProperties", [])
            if props:
                lines.append(f"  - {name}: 属性包括 {', '.join(props)}")
            else:
                lines.append(f"  - {name}")

        lines.append("\n## Relationships (关系定义):")
        for rel_type, connections in self.relationships.items():
            sources = set(c["source"] for c in connections)
            targets = set(c["target"] for c in connections)
            lines.append(
                f"  - {rel_type}: {', '.join(sources)} -> {', '.join(targets)}"
            )

        return "\n".join(lines)

    def get_schema_summary(self) -> dict:
        """获取 Schema 概要，用于 LLM 上下文"""
        return {
            "classes": list(self.classes.keys()),
            "relationships": list(self.relationships.keys()),
            "class_details": self.classes,
            "relationship_details": self.relationships,
        }
