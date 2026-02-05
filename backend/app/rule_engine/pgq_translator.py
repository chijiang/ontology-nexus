# backend/app/rule_engine/pgq_translator.py
"""
SQL/PGQ (Property Graph Query) 翻译器

将规则引擎的 AST 节点转换为 SQL/PGQ 查询。
替代原有的 CypherTranslator，支持 PostgreSQL 18 的原生图查询。

SQL/PGQ 参考：
- ISO SQL:2023 标准
- PostgreSQL 18 GRAPH_TABLE 语法
"""

from typing import Any, Optional, List, Tuple
from app.rule_engine.models import ForClause


class PGQTranslator:
    """将规则引擎 AST 转换为 SQL/PGQ 查询

    SQL/PGQ 使用 GRAPH_TABLE 函数进行图模式匹配。
    语法示例：
        SELECT * FROM GRAPH_TABLE(
            my_graph
            MATCH (a:Person)-[r:knows]->(b:Person)
            WHERE a.name = 'Alice'
            COLUMNS(a.id, b.id)
        )
    """

    def __init__(self):
        """初始化翻译器"""
        self._bound_vars: dict[str, tuple[str, str]] = {}
        self._param_counter = 0

    def translate_for(self, for_clause: ForClause) -> str:
        """将 FOR 子句转换为 SQL/PGQ 查询

        Args:
            for_clause: FOR 子句 AST

        Returns:
            SQL 查询字符串
        """
        var = for_clause.variable
        entity_type = for_clause.entity_type
        condition = for_clause.condition

        # 由于 PostgreSQL 18 的 GRAPH_TABLE 需要 property graph 定义
        # 这里我们使用传统 SQL JOIN 作为兼容实现
        # 如果使用原生 GRAPH_TABLE，需要先 CREATE PROPERTY GRAPH

        # 构建 SELECT 查询
        query = f"SELECT e.*\nFROM graph_entities e\n"
        query += f"WHERE e.entity_type = '{entity_type}'\n"
        query += f"AND e.is_instance = true\n"

        if condition:
            where_clause = self.translate_condition(condition)
            if where_clause:
                query += f"AND {where_clause}\n"

        return query

    def translate_condition(self, condition: Any) -> str:
        """转换条件表达式为 SQL WHERE 子句

        Args:
            condition: AST 表达式节点

        Returns:
            SQL WHERE 子句片段
        """
        if condition is None:
            return ""

        if isinstance(condition, tuple):
            op = condition[0]

            if op == "op":
                # 二元操作: ("op", operator, left, right)
                _, operator, left, right = condition
                return self._translate_binary_op(operator, left, right)

            elif op == "and":
                # AND: ("and", left, right)
                _, left, right = condition
                left_sql = self.translate_condition(left)
                right_sql = self.translate_condition(right)
                return f"({left_sql} AND {right_sql})"

            elif op == "or":
                # OR: ("or", left, right)
                _, left, right = condition
                left_sql = self.translate_condition(left)
                right_sql = self.translate_condition(right)
                return f"({left_sql} OR {right_sql})"

            elif op == "not":
                # NOT: ("not", expr)
                _, expr = condition
                expr_sql = self.translate_condition(expr)
                return f"NOT ({expr_sql})"

            elif op == "is_null":
                # IS NULL / IS NOT NULL: ("is_null", expr, is_not)
                _, expr, is_not = condition
                expr_sql = self._translate_value(expr)
                if is_not:
                    return f"{expr_sql} IS NOT NULL"
                return f"{expr_sql} IS NULL"

            elif op == "id":
                # 标识符/路径: ("id", path)
                _, path = condition
                return self._translate_path(path)

            elif op == "exists":
                # 存在性检查: ("exists", pattern)
                # 转换为 EXISTS 子查询
                _, pattern = condition
                return self._translate_exists_pattern(pattern)

            elif op == "call":
                # 函数调用: ("call", function_name, args)
                _, func_name, args = condition
                return self._translate_function_call(func_name, args)

        # 处理字面值
        return self._translate_value(condition)

    def _translate_binary_op(self, operator: str, left: Any, right: Any) -> str:
        """翻译二元操作

        Args:
            operator: 操作符
            left: 左操作数
            right: 右操作数

        Returns:
            SQL 表达式
        """
        left_sql = self._translate_value(left)
        right_sql = self._translate_value(right)

        # 处理 IN 操作符
        if operator == "IN":
            if isinstance(right, (list, tuple)):
                items = [self._translate_value(item) for item in right]
                right_sql = "(" + ", ".join(items) + ")"
            return f"{left_sql} IN {right_sql}"

        # 处理关系操作符（图模式中的关系遍历）
        # 例如: po -[orderedFrom]-> s
        if isinstance(operator, list) and len(operator) >= 2:
            rel_name = operator[1] if len(operator) > 1 else ""
            direction = operator[2] if len(operator) > 2 else (operator[0] if len(operator) > 0 else "->")

            # 这是一个图模式，需要转换为 EXISTS 子查询
            return self._translate_relationship_pattern(left_sql, rel_name, direction, right_sql)

        # 映射操作符到 SQL
        op_map = {
            "==": "=",
            "!=": "<>",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
        }

        sql_op = op_map.get(str(operator), str(operator))
        return f"{left_sql} {sql_op} {right_sql}"

    def _translate_relationship_pattern(
        self, left: str, rel_name: str, direction: str, right: str
    ) -> str:
        """翻译关系模式为 EXISTS 子查询

        例如: po -[orderedFrom]-> s
        转换为:
            EXISTS (
                SELECT 1 FROM graph_relationships r
                JOIN graph_entities t ON t.id = r.target_id
                WHERE r.source_id = (SELECT id FROM graph_entities WHERE name = 'po')
                AND r.relationship_type = 'orderedFrom'
                AND t.name = 's'
            )

        Args:
            left: 源变量名
            rel_name: 关系类型
            direction: 方向 ("->", "<-", "-")
            right: 目标变量名

        Returns:
            SQL EXISTS 表达式
        """
        # 检查是否有绑定的变量
        left_bound = left in self._bound_vars
        right_bound = right in self._bound_vars

        if direction == "->":
            # 左 -> 右
            if left_bound:
                # 左边已绑定，检查右边
                left_type, left_id = self._bound_vars[left]
                return self._exists_relationship_from_bound(
                    left, left_id, rel_name, right
                )
            else:
                return f"EXISTS (SELECT 1 FROM graph_relationships r WHERE r.relationship_type = '{rel_name}')"

        elif direction == "<-":
            # 左 <- 右
            if right_bound:
                right_type, right_id = self._bound_vars[right]
                return self._exists_relationship_to_bound(
                    right, right_id, rel_name, left
                )
            else:
                return f"EXISTS (SELECT 1 FROM graph_relationships r WHERE r.relationship_type = '{rel_name}')"

        else:
            # 无向
            return f"EXISTS (SELECT 1 FROM graph_relationships r WHERE r.relationship_type = '{rel_name}')"

    def _exists_relationship_from_bound(
        self, source_var: str, source_id: str, rel_type: str, target_var: str
    ) -> str:
        """生成从已绑定变量出发的关系 EXISTS 查询"""
        return f"""EXISTS (
            SELECT 1 FROM graph_relationships r
            JOIN graph_entities e ON e.id = r.target_id
            WHERE r.source_id = {source_id}
            AND r.relationship_type = '{rel_type}'
            AND e.name = '{target_var}'
        )"""

    def _exists_relationship_to_bound(
        self, target_var: str, target_id: str, rel_type: str, source_var: str
    ) -> str:
        """生成指向已绑定变量的关系 EXISTS 查询"""
        return f"""EXISTS (
            SELECT 1 FROM graph_relationships r
            JOIN graph_entities e ON e.id = r.source_id
            WHERE r.target_id = {target_id}
            AND r.relationship_type = '{rel_type}'
            AND e.name = '{source_var}'
        )"""

    def _translate_path(self, path: str) -> str:
        """翻译属性路径

        例如: "po.status" -> "e.properties->>'status'"

        Args:
            path: 点分隔的属性路径

        Returns:
            SQL 属性访问表达式
        """
        parts = path.split(".")
        if not parts:
            return "null"

        var = parts[0]
        if len(parts) == 1:
            return var

        # 处理属性访问: properties->>'key'
        # 假设使用别名 e 表示当前实体
        prop_path = "->>".join([f"'{p}'" for p in parts[1:]])
        return f"e.properties->{prop_path}"

    def _translate_exists_pattern(self, pattern: Any) -> str:
        """翻译存在性检查模式

        Args:
            pattern: 图模式 AST

        Returns:
            SQL EXISTS 表达式
        """
        if not isinstance(pattern, (list, tuple)):
            return ""

        # 解析模式: (node1, rel1, node2, ...)
        # 简化实现：返回一个通用的 EXISTS
        return "EXISTS (SELECT 1)"

    def _translate_function_call(self, func_name: str, args: List[Any]) -> str:
        """翻译函数调用

        Args:
            func_name: 函数名
            args: 参数列表

        Returns:
            SQL 函数调用表达式
        """
        arg_list = [self._translate_value(arg) for arg in args]
        return f"{func_name}({', '.join(arg_list)})"

    def _translate_value(self, value: Any) -> str:
        """翻译值为 SQL 字面量

        Args:
            value: 值

        Returns:
            SQL 字面量表达式
        """
        if value is None:
            return "null"

        if isinstance(value, str):
            # 检查是否是路径引用
            if "." in value or value in self._bound_vars:
                return self._translate_path(value)
            # 否则是字符串字面量
            return f"'{value}'"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, list):
            items = [self._translate_value(item) for item in value]
            return "(" + ", ".join(items) + ")"

        if isinstance(value, tuple):
            # 处理嵌套元组（AST 节点）
            op = value[0] if value else ""
            if op == "path" or op == "id":
                return self._translate_path(value[1])
            elif op == "call":
                return self._translate_function_call(value[1], value[2])
            # 尝试作为条件翻译
            return self.translate_condition(value)

        # 回退：转换为字符串
        return str(value)

    # ==================== 变量绑定 ====================

    def bind_variable(self, var: str, entity_type: str, entity_id: str) -> None:
        """绑定外部作用域变量用于嵌套查询

        Args:
            var: 变量名
            entity_type: 实体类型
            entity_id: 实体 ID
        """
        self._bound_vars[var] = (entity_type, entity_id)

    def unbind_variable(self, var: str) -> None:
        """解除绑定变量

        Args:
            var: 变量名
        """
        if var in self._bound_vars:
            del self._bound_vars[var]

    def clear_bound_vars(self) -> None:
        """清除所有绑定变量"""
        self._bound_vars.clear()

    def _get_next_param(self) -> str:
        """获取下一个参数名

        Returns:
            参数名如 param0, param1
        """
        param_name = f"param{self._param_counter}"
        self._param_counter += 1
        return param_name

    # ==================== GRAPH_TABLE 支持 ====================

    def translate_graph_table(
        self,
        match_pattern: str,
        where_clause: Optional[str] = None,
        columns: Optional[List[str]] = None,
        graph_name: str = "kg_graph"
    ) -> str:
        """生成 GRAPH_TABLE 查询

        这是 PostgreSQL 18 原生图查询的推荐方式。

        Args:
            match_pattern: MATCH 模式，如 "(a:Person)-[r:knows]->(b:Person)"
            where_clause: WHERE 条件
            columns: 要返回的列
            graph_name: 图名称

        Returns:
            完整的 GRAPH_TABLE SQL 查询
        """
        if columns is None:
            columns = ["*"]

        columns_str = ", ".join(columns)

        query = f"SELECT {columns_str}\n"
        query += f"FROM GRAPH_TABLE(\n"
        query += f"    {graph_name}\n"
        query += f"    MATCH {match_pattern}\n"

        if where_clause:
            query += f"    WHERE {where_clause}\n"

        query += f"    COLUMNS {columns_str}\n"
        query += f")"

        return query


class PGQueryBuilder:
    """PostgreSQL 图查询构建器

    提供更便捷的方式来构建图查询。
    """

    @staticmethod
    def build_neighbor_query(
        start_node: str,
        direction: str = "both",
        rel_types: Optional[List[str]] = None,
        hops: int = 1
    ) -> str:
        """构建邻居查询

        Args:
            start_node: 起始节点名称
            direction: 方向 (outgoing/incoming/both)
            rel_types: 关系类型过滤
            hops: 跳数

        Returns:
            SQL 查询
        """
        if direction == "outgoing":
            join_condition = "r.source_id = e.id"
        elif direction == "incoming":
            join_condition = "r.target_id = e.id"
        else:
            join_condition = "r.source_id = e.id OR r.target_id = e.id"

        rel_filter = ""
        if rel_types:
            rel_filter = f"AND r.relationship_type IN ({', '.join([f"'{rt}'" for rt in rel_types])})"

        return f"""
        SELECT DISTINCT
            n.name,
            n.entity_type,
            n.properties,
            r.relationship_type
        FROM graph_entities e
        JOIN graph_relationships r ON {join_condition}
        JOIN graph_entities n ON (
            CASE WHEN r.source_id = e.id THEN r.target_id ELSE r.source_id END = n.id
        )
        WHERE e.name = '{start_node}'
        AND e.is_instance = true
        {rel_filter}
        LIMIT 100
        """

    @staticmethod
    def build_path_query(start_name: str, end_name: str, max_depth: int = 5) -> str:
        """构建路径查询（使用递归 CTE）

        Args:
            start_name: 起始节点名称
            end_name: 目标节点名称
            max_depth: 最大深度

        Returns:
            SQL 查询
        """
        return f"""
        WITH RECURSIVE path_search AS (
            SELECT
                s.id,
                s.name,
                ARRAY[s.id] as path_ids,
                ARRAY[s.name] as path_names,
                0 as depth
            FROM graph_entities s
            WHERE s.name = '{start_name}' AND s.is_instance = true

            UNION ALL

            SELECT
                CASE
                    WHEN r.source_id = ps.id THEN r.target_id
                    ELSE r.source_id
                END as id,
                CASE
                    WHEN r.source_id = ps.id THEN t.name
                    ELSE s.name
                END as name,
                ps.path_ids || CASE WHEN r.source_id = ps.id THEN r.target_id ELSE r.source_id END,
                ps.path_names || CASE WHEN r.source_id = ps.id THEN t.name ELSE s.name END,
                ps.depth + 1
            FROM path_search ps
            JOIN graph_relationships r ON (r.source_id = ps.id OR r.target_id = ps.id)
            JOIN graph_entities s ON r.source_id = s.id
            JOIN graph_entities t ON r.target_id = t.id
            WHERE ps.depth < {max_depth}
            AND NOT (CASE WHEN r.source_id = ps.id THEN r.target_id ELSE r.source_id END = ANY(ps.path_ids))
        )
        SELECT path_names
        FROM path_search
        WHERE name = '{end_name}'
        ORDER BY array_length(path_names, 1) ASC
        LIMIT 1
        """
