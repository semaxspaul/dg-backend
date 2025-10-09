"""
Urban Analysis Agent - ADK Standard
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import get_urban_agent_instruction
from .tools import execute_urban_analysis

# ADK Agent 생성
urban_agent = Agent(
    model=os.getenv("URBAN_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="urban_analysis_agent",
    instruction=get_urban_agent_instruction(),
    tools=[execute_urban_analysis],
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
