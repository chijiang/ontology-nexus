# backend/app/services/agent_tools/mcp_tools.py
import logging
import json
from typing import List, Any, Dict, Optional, Type
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, model_validator
from pydantic.fields import FieldInfo
from sqlalchemy import select
from app.services.mcp_client import MCPClient
from app.models.mcp_config import MCPConfig

logger = logging.getLogger(__name__)

_JSON_SCHEMA_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _coerce_args(data: dict, properties: dict) -> dict:
    """
    Coerce LLM-passed values to the correct Python types based on the JSON schema.
    LLMs often serialize arrays as JSON strings (e.g. '["INDIA"]') and
    integers as numeric strings (e.g. '2025').
    """
    result = {}
    for key, value in data.items():
        if value is None:
            result[key] = value
            continue

        prop = properties.get(key, {})
        # Resolve Optional (anyOf with null)
        if "anyOf" in prop:
            non_null = [t for t in prop["anyOf"] if t.get("type") != "null"]
            prop = non_null[0] if non_null else prop

        expected = prop.get("type", "")

        if isinstance(value, str) and expected == "array":
            stripped = value.strip()
            try:
                parsed = json.loads(stripped)
                value = parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                value = [stripped]  # wrap single plain string

        elif isinstance(value, str) and expected == "integer":
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass

        elif isinstance(value, str) and expected == "number":
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass

        result[key] = value
    return result


def _build_args_schema(input_schema: dict) -> Optional[Type[BaseModel]]:
    """
    Dynamically build a Pydantic BaseModel from an MCP JSON Schema dict.
    Includes a model_validator(mode='before') that coerces string-encoded
    arrays/integers before Pydantic's own type validation runs.
    """
    try:
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        if not properties:
            return None

        fields: Dict[str, Any] = {}
        for name, prop in properties.items():
            schema = prop
            if "anyOf" in schema:
                non_null = [t for t in schema["anyOf"] if t.get("type") != "null"]
                schema = non_null[0] if non_null else schema

            raw_type = schema.get("type", "string")
            py_type = _JSON_SCHEMA_TYPE_MAP.get(raw_type, str)

            description = prop.get("description", "")
            enum = schema.get("enum")
            if enum:
                description += f" Allowed values: {enum}."

            if name not in required:
                fields[name] = (Optional[py_type], Field(default=None, description=description))  # type: ignore
            else:
                fields[name] = (py_type, Field(description=description))

        # Capture properties in closure for the validator
        _properties = properties

        class _CoercingBase(BaseModel):
            @model_validator(mode="before")
            @classmethod
            def _coerce_types(cls, data: Any) -> Any:
                if isinstance(data, dict):
                    return _coerce_args(data, _properties)
                return data

        # Build final model inheriting from the coercing base
        ArgsSchema = type(
            "ArgsSchema",
            (_CoercingBase,),
            {
                "__annotations__": {k: v[0] for k, v in fields.items()},
                **{k: v[1] for k, v in fields.items()},
            },
        )
        return ArgsSchema  # type: ignore
    except Exception as e:
        logger.warning(f"Could not build args_schema from input_schema: {e}")
        return None


class MCPToolRegistry:
    """Registry that converts MCP tools into LangChain StructuredTools."""

    def __init__(self, session_provider):
        self.session_provider = session_provider
        self._tools = []

    async def initialize(self):
        self._tools = []
        async with self.session_provider() as db:
            result = await db.execute(
                select(MCPConfig).where(MCPConfig.is_active == True)
            )
            configs = result.scalars().all()

            for config in configs:
                try:
                    client = MCPClient(config.url)
                    mcp_tools = await client.get_tools()

                    for mcp_tool in mcp_tools:
                        tool_name = mcp_tool["name"]
                        description = mcp_tool.get("description") or tool_name
                        input_schema = mcp_tool.get("input_schema", {})

                        args_schema = _build_args_schema(input_schema)

                        langchain_tool = StructuredTool(
                            name=f"mcp_{config.name}_{tool_name}",
                            description=description,
                            args_schema=args_schema,
                            coroutine=self._create_tool_coroutine(client, tool_name),
                        )
                        self._tools.append(langchain_tool)
                        logger.info(
                            f"Registered MCP tool: {langchain_tool.name} "
                            f"(fields: {list(args_schema.model_fields.keys()) if args_schema else 'none'})"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to load tools from MCP server '{config.name}': {e}"
                    )

    def _create_tool_coroutine(self, client: MCPClient, tool_name: str):
        async def tool_func(**kwargs: Any):
            args_dict = {k: v for k, v in kwargs.items() if v is not None}
            logger.debug(f"Calling MCP tool '{tool_name}' with args: {args_dict}")
            result = await client.call_tool(tool_name, args_dict)
            return str(result)

        return tool_func

    @property
    def tools(self) -> List[StructuredTool]:
        return self._tools
