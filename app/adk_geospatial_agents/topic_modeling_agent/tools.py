"""
Topic Modeling Agent Tools
"""

from typing import Dict, Any
from google.adk.tools import ToolContext

from ..shared.tools.geospatial_tools import get_topic_modeling_analysis

async def execute_topic_modeling_analysis(
    method: str = "lda",
    n_topics: int = 5,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """토픽 모델링 분석을 실행합니다."""
    print(f"📊 [Topic Modeling Agent] Executing analysis: {method}, {n_topics} topics")
    
    result = await get_topic_modeling_analysis(
        method=method,
        n_topics=n_topics,
        tool_context=tool_context
    )
    
    return result
