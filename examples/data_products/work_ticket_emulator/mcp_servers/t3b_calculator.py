"""
T3B Calculator MCP Server

This SSE-based MCP server exposes the T3B (Top 3 Box) calculation pipeline
as a tool that agents can call to analyze work ticket OSAT satisfaction data.

Usage:
    uv run -m work_ticket_emulator.mcp_servers.t3b_calculator
"""

from typing import List, Literal, Optional, Annotated
from fastmcp import FastMCP
from pydantic import Field

from t3bCalculator import t3b_pipeline


# Initialize FastMCP server
mcp = FastMCP(
    "T3B Calculator",
    instructions=(
        "This MCP server provides T3B (Top 3 Box) score analysis for work ticket satisfaction data. "
        "Use the `calculate_t3b` tool to analyze OSAT scores by time period and geography, "
        "and to understand which dimensions (Survey, Location, SOInformation, Product) "
        "contribute most to customer satisfaction scores."
    ),
)


@mcp.tool()
async def calculate_t3b(
    country_name_ops: Annotated[
        Optional[List[Literal["INDIA", "CANADA", "FRANCE"]]],
        Field(
            default=None,
            description="Filter by country. Options: INDIA, CANADA, FRANCE. Leave empty to include all countries.",
        ),
    ] = None,
    geo_ops: Annotated[
        Optional[List[Literal["AP", "NA", "EMEA"]]],
        Field(
            default=None,
            description="Filter by geography. Options: AP (Asia Pacific), NA (North America), EMEA (Europe/Middle East/Africa).",
        ),
    ] = None,
    trans_servdelivery: Annotated[
        Optional[List[Literal["ONS", "CRU", "CIN"]]],
        Field(
            default=None,
            description="Filter by delivery method. Options: ONS (On-site), CRU (Customer Replaceable Unit), CIN (Customer Install).",
        ),
    ] = None,
    program: Annotated[
        Optional[List[Literal["Standard Commercial", "Premier Support"]]],
        Field(
            default=None,
            description="Filter by service program. Options: 'Standard Commercial', 'Premier Support'.",
        ),
    ] = None,
    PX_Region: Annotated[
        Optional[List[Literal["WE"]]],
        Field(
            default=None,
            description="Filter by PX region. Options: WE (Western Europe).",
        ),
    ] = None,
    start_year: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Start year for analysis (e.g. 2024). Leave empty for no lower bound.",
        ),
    ] = None,
    start_month: Annotated[
        Optional[int],
        Field(
            default=None,
            ge=1,
            le=12,
            description="Start month 1-12. Leave empty to default to January.",
        ),
    ] = None,
    end_year: Annotated[
        Optional[int],
        Field(
            default=None,
            description="End year for analysis (e.g. 2025). Leave empty to default to current year.",
        ),
    ] = None,
    end_month: Annotated[
        Optional[int],
        Field(
            default=None,
            ge=1,
            le=12,
            description="End month 1-12. Leave empty to default to current month.",
        ),
    ] = None,
) -> str:
    """
    Calculate T3B (Top 3 Box) score, model R-squared, and feature contribution/importance
    based on filtered work ticket satisfaction data. All filter parameters are optional.

    Returns a formatted report with:
    - Monthly T3B scores (% of respondents scoring 8 or above out of 10)
    - Overall model quality (R² score, higher is better)
    - Dimension importance breakdown (Survey, Location, SOInformation, Product)
    """
    conditions = {}
    if country_name_ops:
        conditions["country_name_ops"] = country_name_ops
    if geo_ops:
        conditions["geo_ops"] = geo_ops
    if trans_servdelivery:
        conditions["trans_servdelivery"] = trans_servdelivery
    if program:
        conditions["program"] = program
    if PX_Region:
        conditions["PX_Region"] = PX_Region
    if start_year is not None:
        conditions["start_year"] = start_year
    if start_month is not None:
        conditions["start_month"] = start_month
    if end_year is not None:
        conditions["end_year"] = end_year
    if end_month is not None:
        conditions["end_month"] = end_month

    try:
        df_t3b, r2, dim_importance = t3b_pipeline(conditions)

        result = [
            "# T3B Calculation Results",
            f"\n## Overall Model Quality (R²): {r2:.4f}",
            "\n## T3B Score by Month (% of respondents scoring 8+):",
        ]

        for month, score in df_t3b.items():
            result.append(f"- {month}: {score}")

        result.append("\n## Feature Contribution by Dimension:")
        for dim, importance in dim_importance.items():
            result.append(f"- {dim}: {importance:.1f}%")

        return "\n".join(result)
    except Exception as e:
        return f"Error calculating T3B: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="sse", port=8801)
