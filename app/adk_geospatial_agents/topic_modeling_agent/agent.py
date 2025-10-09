"""
Topic Modeling Agent - ADK Standard
"""

import os
from google.adk.agents import Agent
from google.genai import types

from .prompts import get_topic_modeling_agent_instruction
from .tools import execute_topic_modeling_analysis

# ADK Agent 생성
topic_modeling_agent = Agent(
    model=os.getenv("TOPIC_MODELING_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="topic_modeling_agent",
    instruction=get_topic_modeling_agent_instruction(),
    tools=[execute_topic_modeling_analysis],
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)
