# backend/app/services/owl_parser.py
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Triple:
    subject: str
    predicate: str
    obj: str


class OWLParser:
    """OWL/TTL 文件解析器"""

    SCHEMA_PREDICATES = {
        RDF.type,
        RDFS.subClassOf,
        RDFS.domain,
        RDFS.range,
        RDFS.subPropertyOf,
        OWL.equivalentClass,
        OWL.disjointWith,
        OWL.equivalentProperty,
        OWL.inverseOf,
    }

    SCHEMA_TYPES = {
        OWL.Class,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.AnnotationProperty,
    }

    def __init__(self, graph: Graph | None = None):
        self.graph = graph or Graph()
        self._schema_entities = set()

    def load_from_file(self, file_path: str) -> None:
        self.graph.parse(file_path, format="turtle")

    def load_from_string(self, data: str) -> None:
        self.graph.parse(data=data, format="turtle")

    def classify_triples(self) -> tuple[List[Triple], List[Triple]]:
        """将三元组分类为 Schema 和 Instance"""
        schema_triples = []
        instance_triples = []

        # 先扫描所有 Schema 实体
        for s, p, o in self.graph:
            if self._is_schema_triple(s, p, o):
                self._schema_entities.add(s)
                if isinstance(o, (str, type(None))):
                    self._schema_entities.add(o)

        # 分类三元组
        for s, p, o in self.graph:
            s_str = str(s)
            p_str = str(p)
            o_str = str(o) if not isinstance(o, type(None)) else None

            if self._is_schema_triple(s, p, o):
                schema_triples.append(Triple(s_str, p_str, o_str))
            else:
                instance_triples.append(Triple(s_str, p_str, o_str))

        return schema_triples, instance_triples

    def _is_schema_triple(self, s, p, o) -> bool:
        """判断是否为 Schema 三元组"""
        # 类型声明：rdf:type
        if p == RDF.type:
            # 如果对象是 Schema 类型（owl:Class, owl:ObjectProperty 等），则是 Schema 三元组
            if o in self.SCHEMA_TYPES:
                return True
            # 如果对象是一个用户定义的类（实例的类型声明），则是 Instance 三元组
            return False

        # 检查 Schema 谓词（subClassOf, domain, range 等）
        if p in self.SCHEMA_PREDICATES:
            return True

        # 检查主体是否是 Schema 实体（类或属性定义）
        if s in self._schema_entities:
            return True

        return False

    def extract_classes(self) -> List[dict]:
        """提取所有类定义"""
        classes = []
        for s, _, o in self.graph.triples((None, RDF.type, OWL.Class)):
            classes.append(
                {
                    "uri": str(s),
                    "name": s.split("#")[-1].split("/")[-1],
                    "label": self._get_label(s),
                }
            )
        return classes

    def extract_properties(self) -> List[dict]:
        """提取所有属性定义"""
        properties = []

        for s, _, o in self.graph.triples((None, RDF.type, OWL.ObjectProperty)):
            properties.append(
                {
                    "uri": str(s),
                    "name": s.split("#")[-1].split("/")[-1],
                    "label": self._get_label(s),
                    "type": "object",
                    "domain": self._get_domain(s),
                    "range": self._get_range(s),
                }
            )

        for s, _, o in self.graph.triples((None, RDF.type, OWL.DatatypeProperty)):
            properties.append(
                {
                    "uri": str(s),
                    "name": s.split("#")[-1].split("/")[-1],
                    "label": self._get_label(s),
                    "type": "data",
                    "domain": self._get_domain(s),
                    "range": self._get_range(s),
                }
            )

        return properties

    def _get_label(self, uri) -> str | None:
        for _, label in self.graph.triples((uri, RDFS.label, None)):
            return str(label)
        return None

    def _get_domain(self, uri) -> str | None:
        for _, _, domain in self.graph.triples((uri, RDFS.domain, None)):
            return str(domain)
        return None

    def _get_range(self, uri) -> str | None:
        for _, _, range_val in self.graph.triples((uri, RDFS.range, None)):
            return str(range_val)
        return None
