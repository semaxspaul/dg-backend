"""
Urban Analysis Agent Tools
"""

from typing import Dict, Any
from google.adk.tools import ToolContext

from ..shared.tools.geospatial_tools import get_urban_area_analysis

async def execute_urban_analysis(
    year: int,
    city_name: str,
    country_name: str,
    coordinates: Dict[str, float] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """도시 지역 분석을 실행합니다."""
    print(f"🏙️ [Urban Agent] Executing analysis: {city_name}, {country_name}, {year}")
    
    result = await get_urban_area_analysis(
        year=year,
        city_name=city_name,
        country_name=country_name,
        coordinates=coordinates,
        tool_context=tool_context
    )
    
    return result
