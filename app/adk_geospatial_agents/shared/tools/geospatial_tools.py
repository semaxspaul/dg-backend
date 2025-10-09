"""
ADK Geospatial Analysis Tools
"""

import os
import requests
from typing import Dict, Any, Optional
from google.adk.tools import ToolContext

# GEE API 엔드포인트
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
    해수면 상승 위험 분석을 수행합니다.
    
    Args:
        year: 분석 연도 (2000-2024)
        threshold: 해수면 상승 임계값 (0.5-5.0m)
        city_name: 도시명
        country_name: 국가명
        coordinates: 좌표 정보 (lat, lng)
        tool_context: ADK 도구 컨텍스트
    
    Returns:
        분석 결과 딕셔너리
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
        
        # 대시보드 업데이트 정보 추가
        dashboard_updates = [
            {
                "type": "sea_level_risk",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"해수면 상승 위험 분석이 완료되었습니다. ({city_name}, {country_name}, {year}년, {threshold}m)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"해수면 상승 위험 분석 중 오류 발생: {str(e)}"
        }

async def get_urban_area_analysis(
    year: int,
    city_name: str,
    country_name: str,
    coordinates: Optional[Dict[str, float]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    도시 지역 분석을 수행합니다.
    
    Args:
        year: 분석 연도 (2000-2024)
        city_name: 도시명
        country_name: 국가명
        coordinates: 좌표 정보 (lat, lng)
        tool_context: ADK 도구 컨텍스트
    
    Returns:
        분석 결과 딕셔너리
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
        
        # 대시보드 업데이트 정보 추가
        dashboard_updates = [
            {
                "type": "urban_analysis",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"도시 지역 분석이 완료되었습니다. ({city_name}, {country_name}, {year}년)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"도시 지역 분석 중 오류 발생: {str(e)}"
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
    인프라 노출 분석을 수행합니다.
    
    Args:
        year: 분석 연도 (2000-2024)
        threshold: 해수면 상승 임계값 (0.5-5.0m)
        city_name: 도시명
        country_name: 국가명
        coordinates: 좌표 정보 (lat, lng)
        tool_context: ADK 도구 컨텍스트
    
    Returns:
        분석 결과 딕셔너리
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
        
        # 대시보드 업데이트 정보 추가
        dashboard_updates = [
            {
                "type": "infrastructure_exposure",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"인프라 노출 분석이 완료되었습니다. ({city_name}, {country_name}, {year}년, {threshold}m)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"인프라 노출 분석 중 오류 발생: {str(e)}"
        }

async def get_topic_modeling_analysis(
    method: str = "lda",
    n_topics: int = 5,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    토픽 모델링 분석을 수행합니다.
    
    Args:
        method: 토픽 모델링 방법 (lda, nmf, bertopic)
        n_topics: 토픽 개수 (2-20)
        tool_context: ADK 도구 컨텍스트
    
    Returns:
        분석 결과 딕셔너리
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
        
        # 대시보드 업데이트 정보 추가
        dashboard_updates = [
            {
                "type": "topic_modeling",
                "data": result.get("data", {}),
                "visualization": result.get("visualization", {})
            }
        ]
        
        return {
            "status": "completed",
            "message": f"토픽 모델링 분석이 완료되었습니다. ({method}, {n_topics}개 토픽)",
            "data": result,
            "dashboard_updates": dashboard_updates
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"토픽 모델링 분석 중 오류 발생: {str(e)}"
        }
