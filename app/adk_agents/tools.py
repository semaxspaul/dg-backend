"""
Google ADK용 지리공간 분석 도구들
"""

import requests
import json
from typing import Dict, Any, Optional
try:
    from google.adk.tools import FunctionTool as Tool
except ImportError:
    # Fallback: 간단한 Tool 클래스 정의
    class Tool:
        def __init__(self, name: str, description: str, function):
            self.name = name
            self.description = description
            self.function = function

class GeospatialAnalysisTools:
    """지리공간 분석을 위한 ADK 도구 모음"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def get_sea_level_risk_analysis(self, 
                                  threshold: float = 2.0, 
                                  year: int = 2020,
                                  min_lat: float = -6.365,
                                  min_lon: float = 106.689,
                                  max_lat: float = -6.089,
                                  max_lon: float = 106.971) -> Dict[str, Any]:
        """
        해수면 상승 위험 분석을 수행합니다.
        
        Args:
            threshold: 해수면 상승 임계값 (미터)
            year: 분석 연도
            min_lat, min_lon, max_lat, max_lon: 분석 영역 좌표
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            params = {
                "threshold": threshold,
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon
            }
            
            response = requests.get(f"{self.base_url}/analysis/slr-risk", params=params)
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json(),
                "parameters": params
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "parameters": params
            }
    
    def get_urban_area_analysis(self, 
                              year: int = 2020,
                              threshold: float = 0.5,
                              min_lat: float = -6.365,
                              min_lon: float = 106.689,
                              max_lat: float = -6.089,
                              max_lon: float = 106.971) -> Dict[str, Any]:
        """
        도시 지역 분석을 수행합니다.
        
        Args:
            year: 분석 연도
            threshold: 도시 지역 임계값
            min_lat, min_lon, max_lat, max_lon: 분석 영역 좌표
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            params = {
                "year": year,
                "threshold": threshold,
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon
            }
            
            response = requests.get(f"{self.base_url}/analysis/urban-area-comprehensive-stats", params=params)
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json(),
                "parameters": params
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "parameters": params
            }
    
    def get_infrastructure_exposure_analysis(self,
                                           year: int = 2020,
                                           threshold: float = 2.0,
                                           min_lat: float = -6.365,
                                           min_lon: float = 106.689,
                                           max_lat: float = -6.089,
                                           max_lon: float = 106.971) -> Dict[str, Any]:
        """
        인프라 노출 분석을 수행합니다.
        
        Args:
            year: 분석 연도
            threshold: 해수면 상승 임계값
            min_lat, min_lon, max_lat, max_lon: 분석 영역 좌표
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            params = {
                "year": year,
                "threshold": threshold,
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon
            }
            
            response = requests.get(f"{self.base_url}/analysis/infrastructure-exposure", params=params)
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json(),
                "parameters": params
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "parameters": params
            }
    
    def get_topic_modeling_analysis(self,
                                  method: str = "lda",
                                  n_topics: int = 5,
                                  file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        토픽 모델링 분석을 수행합니다.
        
        Args:
            method: 토픽 모델링 방법 (lda, nmf, bertopic)
            n_topics: 토픽 수
            file_path: 분석할 파일 경로
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            params = {
                "method": method,
                "n_topics": n_topics
            }
            
            if file_path:
                params["file_path"] = file_path
            
            response = requests.get(f"{self.base_url}/analysis/topic-modeling", params=params)
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json(),
                "parameters": params
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "parameters": params
            }

# ADK 도구 인스턴스 생성
geospatial_tools = GeospatialAnalysisTools()

# ADK Tool 객체들 생성
sea_level_risk_tool = Tool(
    func=geospatial_tools.get_sea_level_risk_analysis
)

urban_analysis_tool = Tool(
    func=geospatial_tools.get_urban_area_analysis
)

infrastructure_tool = Tool(
    func=geospatial_tools.get_infrastructure_exposure_analysis
)

topic_modeling_tool = Tool(
    func=geospatial_tools.get_topic_modeling_analysis
)
