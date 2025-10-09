"""
Main Agent Tools
"""

import os
from typing import Dict, Any
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from ..sea_level_agent.agent import sea_level_agent
from ..urban_agent.agent import urban_agent
from ..infrastructure_agent.agent import infrastructure_agent
from ..topic_modeling_agent.agent import topic_modeling_agent
from ..shared.utils.parameter_collector import parameter_collector

async def call_sea_level_agent(
    request: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Call sea level rise analysis agent."""
    print(f"🌊 [Main Agent] Calling sea level agent with: {request}")
    
    agent_tool = AgentTool(agent=sea_level_agent)
    result = await agent_tool.run_async(
        args={"request": request},
        tool_context=tool_context
    )
    
    return result

async def call_urban_agent(
    request: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Call urban analysis agent."""
    print(f"🏙️ [Main Agent] Calling urban agent with: {request}")
    
    agent_tool = AgentTool(agent=urban_agent)
    result = await agent_tool.run_async(
        args={"request": request},
        tool_context=tool_context
    )
    
    return result

async def call_infrastructure_agent(
    request: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Call infrastructure analysis agent."""
    print(f"🏗️ [Main Agent] Calling infrastructure agent with: {request}")
    
    agent_tool = AgentTool(agent=infrastructure_agent)
    result = await agent_tool.run_async(
        args={"request": request},
        tool_context=tool_context
    )
    
    return result

async def call_topic_modeling_agent(
    request: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Call topic modeling agent."""
    print(f"📊 [Main Agent] Calling topic modeling agent with: {request}")
    
    agent_tool = AgentTool(agent=topic_modeling_agent)
    result = await agent_tool.run_async(
        args={"request": request},
        tool_context=tool_context
    )
    
    return result

async def collect_parameters(
    message: str,
    analysis_type: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Perform parameter collection."""
    print(f"🔧 [Main Agent] Collecting parameters for {analysis_type}")
    
    # Get existing parameters
    existing_params = tool_context.state.get("collected_params", {})
    
    # Collect parameters
    result = parameter_collector.collect_parameters(
        message, analysis_type, existing_params
    )
    
    # Update state
    tool_context.state["collected_params"] = result["params"]
    tool_context.state["analysis_type"] = analysis_type
    
    return result

async def detect_analysis_intent(
    message: str,
    callback_context
) -> Dict[str, Any]:
    """Detect analysis intent."""
    print(f"🔍 [Main Agent] Detecting analysis intent for: {message}")
    
    message_lower = message.lower()
    
    # Sea level rise related keywords
    sea_level_keywords = [
        "sea level", "slr", "해수면", "해수면 상승", "sea level rise", 
        "해수면 상승 위험", "해수면 상승 분석", "해수면 상승 위험 분석"
    ]
    
    # Urban analysis related keywords
    urban_keywords = [
        "urban", "도시", "도시지역", "도시 분석", "도시 지역 분석",
        "urban analysis", "도시 확장", "도시화"
    ]
    
    # Infrastructure analysis related keywords
    infrastructure_keywords = [
        "infrastructure", "인프라", "인프라 노출", "인프라 분석",
        "infrastructure exposure", "인프라 노출 분석"
    ]
    
    # Topic modeling related keywords
    topic_modeling_keywords = [
        "topic modeling", "토픽", "토픽 모델링", "토픽 분석",
        "topic analysis", "텍스트 분석"
    ]
    
    # Keyword matching
    if any(keyword in message_lower for keyword in sea_level_keywords):
        return {"intent": "sea_level_rise", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in urban_keywords):
        return {"intent": "urban_analysis", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in infrastructure_keywords):
        return {"intent": "infrastructure_analysis", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in topic_modeling_keywords):
        return {"intent": "topic_modeling", "confidence": 0.9}
    
    return {"intent": None, "confidence": 0.0}
