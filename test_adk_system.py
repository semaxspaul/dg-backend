"""
ADK System Test Script
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.adk_geospatial_agents import main_agent
from app.adk_geospatial_agents.shared.utils.parameter_collector import parameter_collector
from app.adk_geospatial_agents.shared.utils.location_matcher import location_matcher

async def test_adk_system():
    """ADK 시스템 테스트"""
    print("🧪 Testing ADK Geospatial Analysis System...")
    
    # 1. Location Matcher 테스트
    print("\n1. Testing Location Matcher...")
    location_result = location_matcher.find_city("Seoul")
    print(f"   Seoul search result: {location_result}")
    
    country_result = location_matcher.find_country("South Korea")
    print(f"   South Korea search result: {country_result}")
    
    # 2. Parameter Collector 테스트
    print("\n2. Testing Parameter Collector...")
    param_result = parameter_collector.collect_parameters(
        "I want to analyze sea level rise in Seoul, South Korea for 2020 with 1.5m threshold",
        "sea_level_rise"
    )
    print(f"   Parameter collection result: {param_result}")
    
    # 3. Main Agent 테스트 (기본 구조 확인)
    print("\n3. Testing Main Agent Structure...")
    print(f"   Agent name: {main_agent.name}")
    print(f"   Agent model: {main_agent.model}")
    print(f"   Number of tools: {len(main_agent.tools)}")
    print(f"   Tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in main_agent.tools]}")
    
    print("\n✅ ADK System test completed!")

if __name__ == "__main__":
    asyncio.run(test_adk_system())
