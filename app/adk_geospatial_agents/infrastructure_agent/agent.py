"""
Infrastructure Analysis Agent - ADK Standard
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import get_infrastructure_agent_instruction
from .tools import execute_infrastructure_analysis

# ADK Agent 생성
infrastructure_agent = Agent(
    model=os.getenv("INFRASTRUCTURE_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="infrastructure_analysis_agent",
    instruction=get_infrastructure_agent_instruction(),
    tools=[execute_infrastructure_analysis],
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
