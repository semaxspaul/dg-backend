"""
ADK Parameter Collection Utility
"""

import re
from typing import Dict, Any, List, Optional
from .location_matcher import location_matcher

class ParameterCollector:
    """분석에 필요한 매개변수를 수집하는 유틸리티 클래스"""
    
    def __init__(self):
        self.required_params = {
            "sea_level_rise": ["year", "threshold", "city_name", "country_name"],
            "urban_analysis": ["year", "city_name", "country_name"],
            "infrastructure_analysis": ["year", "threshold", "city_name", "country_name"],
            "topic_modeling": ["method", "n_topics"]
        }
        
        self.valid_years = list(range(2000, 2025))
        self.valid_thresholds = (0.5, 5.0)
    
    async def _extract_parameters(self, message: str, analysis_type: str, existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """사용자 메시지에서 매개변수 추출"""
        extracted = {}
        message_lower = message.lower()
        
        # 연도 추출
        year_patterns = [
            r'(\d{4})',
            r'year\s*:?\s*(\d{4})',
            r'in\s+(\d{4})',
            r'(\d{4})\s*year',
            r'(\d{4})\s*년'  # 한국어 "년" 패턴 추가
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, message_lower)
            if match:
                year = int(match.group(1))
                if year in self.valid_years:
                    extracted['year'] = year
                    break
        
        # 임계값 추출
        threshold_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:meter|m|meters|미터)', # 한국어 "미터" 패턴 추가
            r'threshold\s*:?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*m\s*threshold'
        ]
        
        for pattern in threshold_patterns:
            match = re.search(pattern, message_lower)
            if match:
                threshold = float(match.group(1))
                if self.valid_thresholds[0] <= threshold <= self.valid_thresholds[1]:
                    extracted['threshold'] = threshold
                    break
        
        # 위치 정보 추출 (도시/국가)
        # 먼저 도시 검색 시도
        city_result = location_matcher.extract_location_from_message(message, "city")
        if city_result["found"]:
            if city_result.get("exact_match", False):
                extracted['city_name'] = city_result["city"]
                extracted['country_name'] = city_result["country"]
                extracted['coordinates'] = city_result["coordinates"]
                # 성공적으로 위치를 찾았으므로 기존 제안 및 오류 제거
                if existing_params:
                    for key in ['location_error', 'suggestion_message', 'suggested_city', 'suggested_country']:
                        if key in existing_params:
                            del existing_params[key]
            else:
                # 유사한 도시 제안
                extracted['suggested_city'] = city_result.get("suggested_city")
                extracted['suggested_country'] = city_result.get("suggested_country")
                extracted['suggestion_message'] = city_result.get("message")
        else:
            # 도시를 찾지 못한 경우 국가 검색 시도
            country_result = location_matcher.extract_location_from_message(message, "country")
            if country_result["found"]:
                if country_result.get("exact_match", False):
                    extracted['country_name'] = country_result["country"]
                    # 해당 국가의 주요 도시들 제안
                    if country_result.get("cities"):
                        extracted['suggested_cities'] = country_result["cities"]
                    # 성공적으로 위치를 찾았으므로 기존 제안 및 오류 제거
                    if existing_params:
                        for key in ['location_error', 'suggestion_message', 'suggested_city', 'suggested_country']:
                            if key in existing_params:
                                del existing_params[key]
                else:
                    # 유사한 국가 제안
                    extracted['suggested_country'] = country_result.get("suggested_country")
                    extracted['suggestion_message'] = country_result.get("message")
            else:
                # 위치 정보를 찾을 수 없음
                extracted['location_error'] = "위치 정보를 찾을 수 없습니다."
        
        # 토픽 모델링 매개변수
        if analysis_type == "topic_modeling":
            # 방법 추출
            method_patterns = [
                r'\b(lda|nmf|bertopic)\b',
                r'method\s*:?\s*(lda|nmf|bertopic)'
            ]
            for pattern in method_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    extracted['method'] = match.group(1)
                    break
            
            # 토픽 개수 추출
            n_topics_patterns = [
                r'(\d+)\s*(?:topics|topic)',
                r'n_topics\s*:?\s*(\d+)'
            ]
            for pattern in n_topics_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    n_topics = int(match.group(1))
                    if 2 <= n_topics <= 20:
                        extracted['n_topics'] = n_topics
                        break
        
        return extracted
    
    def _validate_parameters(self, params: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """매개변수 검증"""
        required = self.required_params.get(analysis_type, [])
        missing = []
        invalid = []
        
        for param in required:
            if param not in params or params[param] is None:
                missing.append(param)
            elif param == "year" and params[param] not in self.valid_years:
                invalid.append(f"year must be between 2000-2024, got {params[param]}")
            elif param == "threshold" and not (self.valid_thresholds[0] <= params[param] <= self.valid_thresholds[1]):
                invalid.append(f"threshold must be between {self.valid_thresholds[0]}-{self.valid_thresholds[1]}, got {params[param]}")
        
        # location_error가 있지만 city_name과 country_name이 모두 있으면 location_error는 무시
        if 'location_error' in params and 'city_name' in params and 'country_name' in params:
            if 'location' in missing:
                missing.remove('location')
            if 'location_error' in missing:
                missing.remove('location_error')

        return {
            "valid": len(missing) == 0 and len(invalid) == 0,
            "missing": missing,
            "invalid": invalid,
            "params": params
        }
    
    def are_all_parameters_collected(self, params: Dict[str, Any], analysis_type: str) -> bool:
        """모든 필수 매개변수가 수집되었는지 확인"""
        validation = self._validate_parameters(params, analysis_type)
        return validation["valid"] and len(validation["missing"]) == 0

    async def collect_parameters(self, message: str, analysis_type: str, existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """매개변수 수집 메인 메서드"""
        if existing_params is None:
            existing_params = {}
        
        # 새로 추출된 매개변수
        extracted = await self._extract_parameters(message, analysis_type, existing_params)
        
        # 기존 매개변수와 병합
        all_params = {**existing_params, **extracted}
        
        # location_error가 있지만 city_name과 country_name이 모두 있으면 location_error 제거
        if ('location_error' in all_params and 
            'city_name' in all_params and 'country_name' in all_params and
            all_params['city_name'] and all_params['country_name']):
            del all_params['location_error']
        
        # 검증
        validation = self._validate_parameters(all_params, analysis_type)
        
        return {
            "params": all_params,
            "validation": validation,
            "needs_more_info": not validation["valid"]
        }
    
    def generate_questions(self, missing_params: List[str], analysis_type: str) -> str:
        """누락된 매개변수에 대한 질문 생성"""
        questions = {
            "year": "어떤 연도로 분석하시겠습니까? (예: 2020, 2018)",
            "threshold": "해수면 상승 임계값을 설정해주세요. (예: 1.0m, 2.5m)",
            "city_name": "어떤 도시를 분석하시겠습니까? (예: Seoul, Busan, New York)",
            "country_name": "어떤 국가를 분석하시겠습니까? (예: South Korea, United States)",
            "method": "토픽 모델링 방법을 선택해주세요. (lda, nmf, bertopic)",
            "n_topics": "몇 개의 토픽으로 분석하시겠습니까? (예: 5, 10)"
        }
        
        if missing_params:
            return questions.get(missing_params[0], f"{missing_params[0]} 정보를 입력해주세요.")
        return "추가 정보가 필요합니다."

# 전역 인스턴스 생성
parameter_collector = ParameterCollector()
