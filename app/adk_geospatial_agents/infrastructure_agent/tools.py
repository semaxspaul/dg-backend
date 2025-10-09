"""
Infrastructure Analysis Agent Tools
"""

from typing import Dict, Any
from google.adk.tools import ToolContext

from ..shared.tools.geospatial_tools import get_infrastructure_exposure_analysis

async def execute_infrastructure_analysis(
    year: int,
    threshold: float,
    city_name: str,
    country_name: str,
    coordinates: Dict[str, float] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """인프라 노출 분석을 실행합니다."""
    print(f"🏗️ [Infrastructure Agent] Executing analysis: {city_name}, {country_name}, {year}, {threshold}m")
    
    result = await get_infrastructure_exposure_analysis(
        year=year,
        threshold=threshold,
        city_name=city_name,
        country_name=country_name,
        coordinates=coordinates,
        tool_context=tool_context
    )
    
    return result
