from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.tools import BaseTool
from typing import Optional, Dict, Any
import requests
import json
import os

class GEETool(BaseTool):
    name: str = "geospatial_analysis"
    description: str = """
    Perform geospatial analysis using Google Earth Engine. 
    Use this tool when users request:
    - Sea level rise risk analysis
    - Urban area analysis
    - Population exposure analysis
    - Any geographic or spatial data analysis
    
    Available analysis types:
    1. slr-risk: Sea level rise risk analysis
    2. urban-area: Urban area analysis for a specific year
    3. urban-area-comprehensive: Comprehensive urban area analysis with time series
    4. population-exposure: Population exposure to sea level rise
    """
    
    def _run(self, analysis_type: str, **kwargs) -> str:
        """Execute GEE analysis based on user request"""
        try:
            base_url = "http://localhost:8000/analysis"
            
            if analysis_type == "slr-risk":
                threshold = kwargs.get('threshold', 2.0)
                response = requests.get(f"{base_url}/slr-risk?threshold={threshold}")
                if response.status_code == 200:
                    return f"✅ Sea level rise risk analysis completed with threshold {threshold}m. Map URL generated."
                else:
                    return f"❌ Failed to generate sea level rise risk map: {response.text}"
                    
            elif analysis_type == "urban-area-comprehensive":
                start_year = kwargs.get('start_year', 2014)
                end_year = kwargs.get('end_year', 2020)
                threshold = kwargs.get('threshold', 2.0)
                response = requests.get(f"{base_url}/urban-area-comprehensive-stats?start_year={start_year}&end_year={end_year}&threshold={threshold}")
                if response.status_code == 200:
                    data = response.json()
                    summary = data['summary']
                    return f"""✅ Comprehensive urban area analysis completed for {start_year}-{end_year}:
• Urban area ({end_year}): {summary['urban_area_end_year']:.1f} km²
• Urbanization: {summary['urbanization_pct']:.1f}%
• Population in urban area: {summary['population_in_urban']:,.0f}
• Urban area at risk: {summary['urban_area_in_risk_end_year']:.1f} km²
• Population at risk: {summary['population_in_urban_risk']:,.0f}"""
                else:
                    return f"❌ Failed to generate comprehensive urban area analysis: {response.text}"
                    
            else:
                return f"❌ Unknown analysis type: {analysis_type}. Available types: slr-risk, urban-area-comprehensive, infrastructure-exposure, topic-modeling"
                
        except Exception as e:
            return f"❌ Error performing geospatial analysis: {str(e)}"

class DataGroundAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.tools = [
            GEETool()
        ]
        
        self.system_message = SystemMessage(content="""You are DataGround AI Assistant, a specialized geospatial analytics assistant.

Your capabilities:
1. Perform geospatial analysis using Google Earth Engine
2. Analyze sea level rise risk, urban development, and population exposure
3. Provide insights on Jakarta's urban expansion and vulnerability

When users request geospatial analysis, automatically use the geospatial_analysis tool to:
- Generate maps and statistics
- Provide comprehensive analysis results
- Explain the findings in simple terms

Always be helpful, informative, and proactive in suggesting relevant analyses.""")

        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            system_message=self.system_message
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def process_message(self, user_message: str) -> str:
        """Process user message and return AI response with automatic GEE analysis if needed"""
        try:
            # Check if message contains geospatial analysis keywords
            geo_keywords = [
                'sea level', 'urban', 'population', 'risk', 'analysis', 'map',
                'jakarta', 'geographic', 'spatial', 'elevation', 'threshold',
                'urbanization', 'expansion', 'exposure', 'vulnerability'
            ]
            
            message_lower = user_message.lower()
            is_geo_request = any(keyword in message_lower for keyword in geo_keywords)
            
            if is_geo_request:
                # Use agent for geospatial requests
                response = self.agent_executor.invoke({"input": user_message})
                return response["output"]
            else:
                # Use regular chat for non-geospatial requests
                return self._regular_chat_response(user_message)
                
        except Exception as e:
            return f"I encountered an error while processing your request: {str(e)}. Please try again."
    
    def _regular_chat_response(self, user_message: str) -> str:
        """Handle regular chat messages without geospatial analysis"""
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are DataGround AI Assistant. Help users with general questions about the platform, data analysis, and geospatial concepts. Be friendly and informative."),
                SystemMessage(content=user_message)
            ])
            return response.content
        except Exception as e:
            return f"I'm having trouble processing your message right now. Please try again later." 