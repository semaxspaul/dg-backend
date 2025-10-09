"""
Sea Level Rise Agent Tools
"""

from typing import Dict, Any
from google.adk.tools import ToolContext

from ..shared.tools.geospatial_tools import get_sea_level_risk_analysis

async def execute_sea_level_analysis(
    year: int,
    threshold: float,
    city_name: str,
    country_name: str,
    coordinates: Dict[str, float] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """해수면 상승 위험 분석을 실행합니다."""
    print(f"🌊 [Sea Level Agent] Executing analysis: {city_name}, {country_name}, {year}, {threshold}m")
    
    result = await get_sea_level_risk_analysis(
        year=year,
        threshold=threshold,
        city_name=city_name,
        country_name=country_name,
        coordinates=coordinates,
        tool_context=tool_context
    )
    
    return result
