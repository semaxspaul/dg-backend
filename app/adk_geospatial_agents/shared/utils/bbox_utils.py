"""
Bounding Box 계산 유틸리티
좌표와 buffer를 받아서 일관된 bbox를 생성합니다.
"""

from typing import Dict, Any, Tuple

def calculate_bbox(coordinates: Dict[str, Any], buffer: float = 0.25) -> Dict[str, float]:
    """
    좌표와 buffer를 받아서 bbox를 계산합니다.
    
    Args:
        coordinates: {'lat': float, 'lng': float} 형태의 좌표
        buffer: bbox 확장 정도 (degrees)
    
    Returns:
        bbox 파라미터 딕셔너리
    """
    lat = coordinates.get("lat", 35.18)
    lng = coordinates.get("lng", 129.075)
    
    return {
        "min_lat": lat - buffer,
        "min_lon": lng - buffer,
        "max_lat": lat + buffer,
        "max_lon": lng + buffer
    }

def calculate_bbox_from_coords(lat: float, lng: float, buffer: float = 0.25) -> Dict[str, float]:
    """
    직접 좌표를 받아서 bbox를 계산합니다.
    
    Args:
        lat: 위도
        lng: 경도
        buffer: bbox 확장 정도 (degrees)
    
    Returns:
        bbox 파라미터 딕셔너리
    """
    return {
        "min_lat": lat - buffer,
        "min_lon": lng - buffer,
        "max_lat": lat + buffer,
        "max_lon": lng + buffer
    }

def get_standard_buffer(analysis_type: str) -> float:
    """
    분석 타입에 따른 표준 buffer 크기를 반환합니다.
    
    Args:
        analysis_type: 분석 타입 ('sea_level_rise', 'urban_analysis', etc.)
    
    Returns:
        표준 buffer 크기 (degrees)
    """
    buffer_map = {
        'sea_level_rise': 0.25,
        'urban_analysis': 0.25,
        'infrastructure_analysis': 0.25,
        'topic_modeling': 0.25
    }
    
    return buffer_map.get(analysis_type, 0.25)  # 기본값 0.25
