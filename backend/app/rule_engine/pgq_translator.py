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

        # Use the variable name as the table alias for consistency with paths
        alias = var

        # 构建 SELECT 查询
        query = f"SELECT {alias}.*\nFROM graph_entities {alias}\n"
        query += f"WHERE {alias}.entity_type = '{entity_type}'\n"
        query += f"AND {alias}.is_instance = true\n"

        if condition:
            # Pass alias context if needed, but currently translate_condition handles it via paths
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

            elif op == "node":
                # 节点模式: ("node", var, type_name)
                # 在 SQL 中通常只使用变量名作为别名
                return str(condition[1])

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
            direction = (
                operator[2]
                if len(operator) > 2
                else (operator[0] if len(operator) > 0 else "->")
            )

            # 这是一个图模式，需要转换为 EXISTS 子查询
            return self._translate_relationship_pattern(
                left_sql, rel_name, direction, right_sql
            )

        if operator == "!=":
            return f"({left_sql} IS NULL OR {left_sql} <> {right_sql})"

        op_map = {
            "==": "=",
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
                # 左边已绑定，检查右边是否也绑定了
                left_type, left_id = self._bound_vars[left]
                if right_bound:
                    right_type, right_id = self._bound_vars[right]
                    return self._exists_relationship_between_bounds(
                        left_id, rel_name, right_id
                    )
                else:
                    return self._exists_relationship_from_bound(
                        left, left_id, rel_name, right
                    )
            elif right_bound:
                # 只有右边绑定，源 <- 目标（反向检查）
                right_type, right_id = self._bound_vars[right]
                return self._exists_relationship_to_bound(
                    right, right_id, rel_name, left
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
        self,
        source_var: str,
        source_id: Any,
        rel_type: str,
        target_var: str,
        target_type: str = None,
        condition: str = None,
    ) -> str:
        """生成从已绑定变量出发的关系 EXISTS 查询"""
        sid = (
            source_id
            if isinstance(source_id, (int, str)) and "." in str(source_id)
            else (source_id if isinstance(source_id, int) else f"'{source_id}'")
        )

        # If target_var is not bound, we need to join graph_entities
        if target_var not in self._bound_vars:
            where_parts = [
                f"r.source_id = {sid}",
                f"r.relationship_type = '{rel_type}'",
                f"r.target_id = {target_var}.id",
            ]
            if target_type:
                where_parts.append(f"{target_var}.entity_type = '{target_type}'")
            if condition:
                where_parts.append(condition)

            return f"""EXISTS (
                SELECT 1 FROM graph_entities {target_var}
                JOIN graph_relationships r ON r.target_id = {target_var}.id
                WHERE {" AND ".join(where_parts)}
            )"""
        else:
            # Both are bound
            where_parts = [
                f"r.source_id = {sid}",
                f"r.relationship_type = '{rel_type}'",
                f"r.target_id = {target_var}.id",  # target_var should be an alias in outer query
            ]
            if condition:
                where_parts.append(condition)

            return f"""EXISTS (
                SELECT 1 FROM graph_relationships r
                WHERE {" AND ".join(where_parts)}
            )"""

    def _exists_relationship_to_bound(
        self,
        target_var: str,
        target_id: Any,
        rel_type: str,
        source_var: str,
        source_type: str = None,
        condition: str = None,
    ) -> str:
        """生成指向已绑定变量的关系 EXISTS 查询"""
        tid = (
            target_id
            if isinstance(target_id, (int, str)) and "." in str(target_id)
            else (target_id if isinstance(target_id, int) else f"'{target_id}'")
        )

        if source_var not in self._bound_vars:
            where_parts = [
                f"r.target_id = {tid}",
                f"r.relationship_type = '{rel_type}'",
                f"r.source_id = {source_var}.id",
            ]
            if source_type:
                where_parts.append(f"{source_var}.entity_type = '{source_type}'")
            if condition:
                where_parts.append(condition)

            return f"""EXISTS (
                SELECT 1 FROM graph_entities {source_var}
                JOIN graph_relationships r ON r.source_id = {source_var}.id
                WHERE {" AND ".join(where_parts)}
            )"""
        else:
            where_parts = [
                f"r.target_id = {tid}",
                f"r.relationship_type = '{rel_type}'",
                f"r.source_id = {source_var}.id",
            ]
            if condition:
                where_parts.append(condition)

            return f"""EXISTS (
                SELECT 1 FROM graph_relationships r
                WHERE {" AND ".join(where_parts)}
            )"""

    def _exists_relationship_between_bounds(
        self, source_id: Any, rel_type: str, target_id: Any
    ) -> str:
        """生成两个已绑定变量之间的关系 EXISTS 查询"""
        sid = source_id if isinstance(source_id, int) else f"{source_id}"
        tid = target_id if isinstance(target_id, int) else f"{target_id}"
        return f"""EXISTS (
            SELECT 1 FROM graph_relationships r
            WHERE r.source_id = {sid}
            AND r.target_id = {tid}
            AND r.relationship_type = '{rel_type}'
        )"""

    def _translate_path(self, path: str) -> str:
        """翻译属性路径

        例如: "po.status" -> "e.properties->>'status'"
        如果是基础字段: "po.id" -> "e.id"

        Args:
            path: 点分隔的属性路径

        Returns:
            SQL 属性访问表达式
        """
        parts = path.split(".")
        if not parts:
            return "null"

        # 映射别名。在目前实现中，主要实体通常用 'e'
        # 在 GRAPH_TABLE 或 JOIN 中可能会有不同别名
        # 这里简化处理，如果是 this 则映射到 e
        var = parts[0]
        # In current RuleEngine implementation, triggering entity uses 'this' or 'e'
        # Nested FORs use their own variable names which correspond to table aliases
        alias = var

        if len(parts) == 1:
            return alias

        attr = parts[1]

        # 基础列名直接访问
        base_cols = {"id", "name", "entity_type", "is_instance", "uri", "properties"}
        if attr in base_cols and len(parts) == 2:
            return f"{alias}.{attr}"

        # 属性访问: properties->'key1'->>'key2'
        # 对 JSONB，最后一级使用 ->> 获取 text，中间级使用 -> 获取 jsonb
        if len(parts) == 2:
            return f"{alias}.properties->>'{attr}'"

        # 多级嵌套
        path_segments = "->".join([f"'{p}'" for p in parts[1:-1]])
        last_segment = f"->>'{parts[-1]}'"
        return f"{alias}.properties->{path_segments}{last_segment}"

    def _translate_pattern(self, pattern: Any) -> str:
        """Entry point for ExpressionEvaluator to translate a pattern (e.g. for EXISTS)."""
        return self._translate_exists_pattern(pattern)

    def _translate_exists_pattern(self, pattern: Any) -> str:
        """翻译存在性检查模式

        Args:
            pattern: 图模式 AST, 例如: [node1, rel, node2, "WHERE", condition]
        """
        if not isinstance(pattern, (list, tuple)) or len(pattern) < 3:
            return "SELECT 1"  # Default truthy for EXISTS if pattern is weird

        # Filter out "WHERE" and condition
        actual_pattern = []
        condition_ast = None
        is_where = False

        for item in pattern:
            if item == "WHERE":
                is_where = True
                continue
            if is_where:
                condition_ast = item
                break
            actual_pattern.append(item)

        if len(actual_pattern) < 3:
            return "SELECT 1"

        # Translate components
        left_node = actual_pattern[0]
        rel_pattern = actual_pattern[1]
        right_node = actual_pattern[2]

        # Format nodes
        left_var = (
            left_node[1]
            if isinstance(left_node, (list, tuple)) and left_node[0] == "node"
            else str(left_node)
        )
        right_var = (
            right_node[1]
            if isinstance(right_node, (list, tuple)) and right_node[0] == "node"
            else str(right_node)
        )
        right_type = (
            right_node[2]
            if isinstance(right_node, (list, tuple)) and right_node[0] == "node"
            else None
        )
        left_type = (
            left_node[2]
            if isinstance(left_node, (list, tuple)) and left_node[0] == "node"
            else None
        )

        # Format relationship
        rel_name = rel_pattern[1] if len(rel_pattern) > 1 else ""
        direction = "->"  # Default
        if rel_pattern[0] == "<-":
            direction = "<-"
        elif rel_pattern[2] == "->":
            direction = "->"
        else:
            direction = "-"

        # Translate condition if present
        condition_sql = (
            self.translate_condition(condition_ast) if condition_ast else None
        )

        # Generate SQL
        left_bound = left_var in self._bound_vars
        right_bound = right_var in self._bound_vars

        if direction == "->":
            if left_bound:
                _, left_id = self._bound_vars[left_var]
                sql = self._exists_relationship_from_bound(
                    left_var, left_id, rel_name, right_var, right_type, condition_sql
                )
            elif right_bound:
                _, right_id = self._bound_vars[right_var]
                sql = self._exists_relationship_to_bound(
                    right_var, right_id, rel_name, left_var, left_type, condition_sql
                )
            else:
                # Neither bound, return a generic join
                sql = f"EXISTS (SELECT 1 FROM graph_entities {left_var} JOIN graph_relationships r ON r.source_id = {left_var}.id JOIN graph_entities {right_var} ON r.target_id = {right_var}.id WHERE r.relationship_type = '{rel_name}'"
                if left_type:
                    sql += f" AND {left_var}.entity_type = '{left_type}'"
                if right_type:
                    sql += f" AND {right_var}.entity_type = '{right_type}'"
                if condition_sql:
                    sql += f" AND {condition_sql}"
                sql += ")"
        elif direction == "<-":
            if right_bound:
                _, right_id = self._bound_vars[right_var]
                sql = self._exists_relationship_from_bound(
                    right_var, right_id, rel_name, left_var, left_type, condition_sql
                )
            elif left_bound:
                _, left_id = self._bound_vars[left_var]
                sql = self._exists_relationship_to_bound(
                    left_var, left_id, rel_name, right_var, right_type, condition_sql
                )
            else:
                sql = f"EXISTS (SELECT 1 FROM graph_entities {right_var} JOIN graph_relationships r ON r.source_id = {right_var}.id JOIN graph_entities {left_var} ON r.target_id = {left_var}.id WHERE r.relationship_type = '{rel_name}'"
                if right_type:
                    sql += f" AND {right_var}.entity_type = '{right_type}'"
                if left_type:
                    sql += f" AND {left_var}.entity_type = '{left_type}'"
                if condition_sql:
                    sql += f" AND {condition_sql}"
                sql += ")"
        else:
            # Unspecified direction
            sql = "EXISTS (SELECT 1)"  # Simplify for now

        # ExpressionEvaluator wraps it in EXISTS(sql) so we return only the inner SELECT if it already starts with EXISTS
        stripped_sql = sql.strip()
        if stripped_sql.upper().startswith("EXISTS") and stripped_sql.endswith(")"):
            # Extract content between EXISTS ( and )
            start = stripped_sql.find("(")
            return stripped_sql[start + 1 : -1].strip()
        return sql

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
        graph_name: str = "kg_graph",
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
        hops: int = 1,
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
