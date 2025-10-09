import openai
import requests
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleDataGroundAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please check your .env file.")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.base_url = "http://localhost:8000/analysis"
    
    def _call_gee_api(self, analysis_type: str, **kwargs) -> str:
        """Execute GEE analysis based on user request"""
        try:
            if analysis_type == "slr-risk":
                threshold = kwargs.get('threshold', 2.0)
                year = kwargs.get('year', 2020)
                
                # Check if user is asking about population at risk
                if 'population' in kwargs.get('user_message', '').lower() or 'people' in kwargs.get('user_message', '').lower():
                    # Call population exposure trend for single year
                    response = requests.get(f"{self.base_url}/population-exposure-trend?start_year={year}&end_year={year}&threshold={threshold}")
                    if response.status_code == 200:
                        data = response.json()
                        total_pop = data['total_population'][0] if data['total_population'] else 0
                        high_risk_pop = data['high_risk_population'][0] if data['high_risk_population'] else 0
                        risk_percentage = (high_risk_pop/total_pop*100) if total_pop > 0 else 0
                        return f"""✅ Sea level rise risk analysis completed for Jakarta in {year} with {threshold}m threshold:

📊 Population Analysis:
• Total population in Jakarta: {total_pop:,.0f} people
• Population at risk from {threshold}m sea level rise: {high_risk_pop:,.0f} people
• Percentage of population at risk: {risk_percentage:.1f}%

This analysis shows how many people would be affected if sea levels rise by {threshold} meters in {year}."""
                    else:
                        return f"❌ Failed to generate population exposure analysis: {response.text}"
                else:
                    # Just return map URL for general SLR risk
                    response = requests.get(f"{self.base_url}/slr-risk?threshold={threshold}")
                    if response.status_code == 200:
                        return f"✅ Sea level rise risk analysis completed with threshold {threshold}m. Map URL generated."
                    else:
                        return f"❌ Failed to generate sea level rise risk map: {response.text}"
                    
            elif analysis_type == "urban-area-comprehensive":
                start_year = kwargs.get('start_year', 2014)
                end_year = kwargs.get('end_year', 2020)
                threshold = kwargs.get('threshold', 2.0)
                response = requests.get(f"{self.base_url}/urban-area-comprehensive-stats?start_year={start_year}&end_year={end_year}&threshold={threshold}")
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
    
    def _extract_analysis_params(self, user_message: str) -> Dict[str, Any]:
        """Extract analysis parameters from user message"""
        message_lower = user_message.lower()
        params = {}
        
        # Extract analysis type
        if 'sea level' in message_lower or 'slr' in message_lower:
            params['analysis_type'] = 'slr-risk'
        elif 'urban' in message_lower and 'comprehensive' in message_lower:
            params['analysis_type'] = 'urban-area-comprehensive'
        elif 'urban' in message_lower:
            params['analysis_type'] = 'urban-area'
        elif 'population' in message_lower and 'exposure' in message_lower:
            params['analysis_type'] = 'population-exposure'
        else:
            return {}
        
        # Extract year parameters
        import re
        year_pattern = r'\b(20\d{2})\b'
        years = re.findall(year_pattern, user_message)
        if years:
            if params['analysis_type'] == 'urban-area-comprehensive' and len(years) >= 2:
                params['start_year'] = int(years[0])
                params['end_year'] = int(years[1])
            else:
                params['year'] = int(years[0])
        
        # Extract threshold
        threshold_pattern = r'(\d+(?:\.\d+)?)\s*(?:meter|m|meters)'
        threshold_match = re.search(threshold_pattern, message_lower)
        if threshold_match:
            params['threshold'] = float(threshold_match.group(1))
        
        return params
    
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
                # Extract parameters and perform analysis
                params = self._extract_analysis_params(user_message)
                if params and 'analysis_type' in params:
                    analysis_type = params.pop('analysis_type')
                    # Add user message to params for context
                    params['user_message'] = user_message
                    result = self._call_gee_api(analysis_type, **params)
                    
                    # Generate contextual response
                    system_prompt = f"""You are DataGround AI Assistant. A user requested geospatial analysis and you've completed it. 
                    
Analysis Result: {result}

Provide a helpful, contextual response that:
1. Acknowledges the analysis completion
2. Explains what was analyzed
3. Mentions key findings if available
4. Suggests next steps or related analyses

Keep the response conversational and informative."""
                    
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0.7
                    )
                    return response.choices[0].message.content
                else:
                    return "I understand you're asking about geospatial analysis, but I need more specific details. Could you please specify what type of analysis you'd like (sea level rise risk, urban area analysis, population exposure, etc.) and for which year(s)?"
            else:
                # Use regular chat for non-geospatial requests
                return self._regular_chat_response(user_message)
                
        except Exception as e:
            return f"I encountered an error while processing your request: {str(e)}. Please try again."
    
    def _regular_chat_response(self, user_message: str) -> str:
        """Handle regular chat messages without geospatial analysis"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are DataGround AI Assistant. Help users with general questions about the platform, data analysis, and geospatial concepts. Be friendly and informative."},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm having trouble processing your message right now. Please try again later." 