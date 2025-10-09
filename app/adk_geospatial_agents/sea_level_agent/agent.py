"""
Sea Level Rise Analysis Agent - ADK Standard
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import get_sea_level_agent_instruction
from .tools import execute_sea_level_analysis

# ADK Agent 생성
sea_level_agent = Agent(
    model=os.getenv("SEA_LEVEL_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="sea_level_rise_agent",
    instruction=get_sea_level_agent_instruction(),
    tools=[execute_sea_level_analysis],
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
