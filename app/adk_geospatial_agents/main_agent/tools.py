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
    """해수면 상승 분석 에이전트를 호출합니다."""
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
    """도시 분석 에이전트를 호출합니다."""
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
    """인프라 분석 에이전트를 호출합니다."""
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
    """토픽 모델링 에이전트를 호출합니다."""
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
    """매개변수 수집을 수행합니다."""
    print(f"🔧 [Main Agent] Collecting parameters for {analysis_type}")
    
    # 기존 매개변수 가져오기
    existing_params = tool_context.state.get("collected_params", {})
    
    # 매개변수 수집
    result = parameter_collector.collect_parameters(
        message, analysis_type, existing_params
    )
    
    # 상태 업데이트
    tool_context.state["collected_params"] = result["params"]
    tool_context.state["analysis_type"] = analysis_type
    
    return result

async def detect_analysis_intent(
    message: str,
    callback_context
) -> Dict[str, Any]:
    """분석 의도를 감지합니다."""
    print(f"🔍 [Main Agent] Detecting analysis intent for: {message}")
    
    message_lower = message.lower()
    
    # 해수면 상승 관련 키워드
    sea_level_keywords = [
        "sea level", "slr", "해수면", "해수면 상승", "sea level rise", 
        "해수면 상승 위험", "해수면 상승 분석", "해수면 상승 위험 분석"
    ]
    
    # 도시 분석 관련 키워드
    urban_keywords = [
        "urban", "도시", "도시지역", "도시 분석", "도시 지역 분석",
        "urban analysis", "도시 확장", "도시화"
    ]
    
    # 인프라 분석 관련 키워드
    infrastructure_keywords = [
        "infrastructure", "인프라", "인프라 노출", "인프라 분석",
        "infrastructure exposure", "인프라 노출 분석"
    ]
    
    # 토픽 모델링 관련 키워드
    topic_modeling_keywords = [
        "topic modeling", "토픽", "토픽 모델링", "토픽 분석",
        "topic analysis", "텍스트 분석"
    ]
    
    # 키워드 매칭
    if any(keyword in message_lower for keyword in sea_level_keywords):
        return {"intent": "sea_level_rise", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in urban_keywords):
        return {"intent": "urban_analysis", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in infrastructure_keywords):
        return {"intent": "infrastructure_analysis", "confidence": 0.9}
    elif any(keyword in message_lower for keyword in topic_modeling_keywords):
        return {"intent": "topic_modeling", "confidence": 0.9}
    
    return {"intent": None, "confidence": 0.0}
