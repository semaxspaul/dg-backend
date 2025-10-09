"""
ADK Geospatial Analysis Tools
"""

import os
import requests
from typing import Dict, Any, Optional
from google.adk.tools import ToolContext

# GEE API endpoint
GEE_API_BASE = "http://localhost:8000/api/analysis"

async def get_sea_level_risk_analysis(
    year: int,
    threshold: float,
    city_name: str,
    country_name: str,
    coordinates: Optional[Dict[str, float]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Performs sea level rise risk analysis.
    
    Args:
        year: Analysis year (2000-2024)
        threshold: Sea level rise threshold (0.5-5.0m)
        city_name: City name
        country_name: Country name
        coordinates: Coordinate information (lat, lng)
        tool_context: ADK tool context
    
    Returns:
        Analysis result dictionary
    """
    try:
        url = f"{GEE_API_BASE}/sea-level-rise-risk"
        payload = {
            "year": year,
            "threshold": threshold,
            "city_name": city_name,
            "country_name": country_name
        }
        
        if coordinates:
            payload.update(coordinates)
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Add dashboard update information
        dashboard_updates = [
            {
                "type": "sea_level_risk",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"Sea level rise risk analysis completed. ({city_name}, {country_name}, {year}, {threshold}m)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error occurred during sea level rise risk analysis: {str(e)}"
        }

async def get_urban_area_analysis(
    year: int,
    city_name: str,
    country_name: str,
    coordinates: Optional[Dict[str, float]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Performs urban area analysis.
    
    Args:
        year: Analysis year (2000-2024)
        city_name: City name
        country_name: Country name
        coordinates: Coordinate information (lat, lng)
        tool_context: ADK tool context
    
    Returns:
        Analysis result dictionary
    """
    try:
        url = f"{GEE_API_BASE}/urban-area-comprehensive"
        payload = {
            "year": year,
            "city_name": city_name,
            "country_name": country_name
        }
        
        if coordinates:
            payload.update(coordinates)
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Add dashboard update information
        dashboard_updates = [
            {
                "type": "urban_analysis",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"Urban area analysis completed. ({city_name}, {country_name}, {year})",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error occurred during urban area analysis: {str(e)}"
        }

async def get_infrastructure_exposure_analysis(
    year: int,
    threshold: float,
    city_name: str,
    country_name: str,
    coordinates: Optional[Dict[str, float]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Performs infrastructure exposure analysis.
    
    Args:
        year: Analysis year (2000-2024)
        threshold: Sea level rise threshold (0.5-5.0m)
        city_name: City name
        country_name: Country name
        coordinates: Coordinate information (lat, lng)
        tool_context: ADK tool context
    
    Returns:
        Analysis result dictionary
    """
    try:
        url = f"{GEE_API_BASE}/infrastructure-exposure"
        payload = {
            "year": year,
            "threshold": threshold,
            "city_name": city_name,
            "country_name": country_name
        }
        
        if coordinates:
            payload.update(coordinates)
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Add dashboard update information
        dashboard_updates = [
            {
                "type": "infrastructure_exposure",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"Infrastructure exposure analysis completed. ({city_name}, {country_name}, {year}, {threshold}m)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error occurred during infrastructure exposure analysis: {str(e)}"
        }

async def get_topic_modeling_analysis(
    method: str = "lda",
    n_topics: int = 5,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Performs topic modeling analysis.
    
    Args:
        method: Topic modeling method (lda, nmf, bertopic)
        n_topics: Number of topics (2-20)
        tool_context: ADK tool context
    
    Returns:
        Analysis result dictionary
    """
    try:
        url = f"{GEE_API_BASE}/topic-modeling"
        payload = {
            "method": method,
            "n_topics": n_topics
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Add dashboard update information
        dashboard_updates = [
            {
                "type": "topic_modeling",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"Topic modeling analysis completed. ({method}, {n_topics} topics)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error occurred during topic modeling analysis: {str(e)}"
        }
