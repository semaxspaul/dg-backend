"""
매개변수 수집을 담당하는 ADK 에이전트
"""

import re
from typing import Dict, Any, List, Optional
from .location_matcher import location_matcher
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool as Tool
except ImportError:
    # Fallback: 간단한 클래스 정의
    class LlmAgent:
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'agent')
            self.model = kwargs.get('model', 'gpt-4')
            self.description = kwargs.get('description', '')
            self.instruction = kwargs.get('instruction', '')
            self.tools = kwargs.get('tools', [])
            self.sub_agents = kwargs.get('sub_agents', [])
    
    class Tool:
        def __init__(self, name: str, description: str, function):
            self.name = name
            self.description = description
            self.function = function

class ParameterCollectorAgent:
    """분석에 필요한 매개변수를 수집하는 에이전트"""
    
    def __init__(self):
        self.required_params = {
            "sea_level_rise": ["year", "threshold", "city_name", "country_name"],
            "urban_analysis": ["year", "city_name", "country_name"],
            "infrastructure_analysis": ["year", "threshold", "city_name", "country_name"],
            "topic_modeling": ["method", "n_topics"]
        }
        
        self.valid_years = list(range(2000, 2025))
        self.valid_thresholds = (0.5, 5.0)
        
        # 매개변수 검증 도구
        self.validation_tool = Tool(
            func=self._validate_parameters
        )
        
        # 매개변수 추출 도구
        self.extraction_tool = Tool(
            func=self._extract_parameters
        )
        
        # ADK 에이전트 생성
        self.agent = LlmAgent(
            name="parameter_collector",
            model="gemini-2.0-flash-exp",
            description="분석에 필요한 매개변수를 수집하고 검증하는 전문 에이전트",
            instruction="""
            당신은 지리공간 분석에 필요한 매개변수를 수집하는 전문 에이전트입니다.
            
            주요 역할:
            1. 사용자 메시지에서 매개변수 추출 (연도, 임계값, 위치 등)
            2. 추출된 매개변수 검증
            3. 누락된 매개변수 식별 및 질문 생성
            4. 수집된 매개변수를 구조화된 형태로 반환
            
            매개변수 유형:
            - year: 분석 연도 (2000-2024)
            - threshold: 해수면 상승 임계값 (0.5-5.0 미터)
            - location: 도시명 또는 좌표
            - method: 토픽 모델링 방법 (lda, nmf, bertopic)
            - n_topics: 토픽 수 (1-20)
            
            항상 사용자에게 친근하고 명확하게 질문하세요.
            """,
            tools=[self.validation_tool, self.extraction_tool]
        )
    
    def _extract_parameters(self, message: str, analysis_type: str, existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
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
            r'(\d+(?:\.\d+)?)\s*(?:meter|m|meters|미터)',
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
        location_result = location_matcher.extract_location_from_message(message)
        
        if location_result["type"] == "city" and location_result["result"]["found"]:
            if location_result["result"]["exact_match"]:
                extracted['city_name'] = location_result["result"]["city"]
                extracted['country_name'] = location_result["result"]["country"]
                extracted['coordinates'] = location_result["result"]["coordinates"]
                # 성공적으로 위치를 찾았으므로 기존 location_error 제거
                if 'location_error' in existing_params:
                    del existing_params['location_error']
            else:
                # 유사한 도시 제안
                extracted['suggested_city'] = location_result["result"]["suggested_city"]
                extracted['suggested_country'] = location_result["result"]["suggested_country"]
                extracted['suggestion_message'] = location_result["result"]["message"]
        
        elif location_result["type"] == "country" and location_result["result"]["found"]:
            if location_result["result"]["exact_match"]:
                extracted['country_name'] = location_result["result"]["country"]
                # 해당 국가의 주요 도시들 제안
                if location_result["result"]["cities"]:
                    extracted['suggested_cities'] = location_result["result"]["cities"]
                # 성공적으로 위치를 찾았으므로 기존 location_error 제거
                if 'location_error' in existing_params:
                    del existing_params['location_error']
            else:
                # 유사한 국가 제안
                extracted['suggested_country'] = location_result["result"]["suggested_country"]
                extracted['suggestion_message'] = location_result["result"]["message"]
        
        elif location_result["type"] == "none":
            # 위치 정보를 찾을 수 없음
            extracted['location_error'] = location_result["result"]["message"]
        
        # 토픽 모델링 매개변수
        if analysis_type == "topic_modeling":
            # 방법 추출
            method_patterns = [
                r'(lda|nmf|bertopic)',
                r'method\s*:?\s*(lda|nmf|bertopic)'
            ]
            
            for pattern in method_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    extracted['method'] = match.group(1)
                    break
            
            # 토픽 수 추출
            topics_patterns = [
                r'(\d+)\s*topics?',
                r'n_topics?\s*:?\s*(\d+)',
                r'topics?\s*:?\s*(\d+)'
            ]
            
            for pattern in topics_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    n_topics = int(match.group(1))
                    if 1 <= n_topics <= 20:
                        extracted['n_topics'] = n_topics
                        break
        
        return extracted
    
    def _validate_parameters(self, params: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """매개변수 검증"""
        required = self.required_params.get(analysis_type, [])
        missing = []
        invalid = []
        
        for param in required:
            if param not in params:
                missing.append(param)
            elif param == "year" and params[param] not in self.valid_years:
                invalid.append(f"year must be between 2000-2024, got {params[param]}")
            elif param == "threshold" and not (self.valid_thresholds[0] <= params[param] <= self.valid_thresholds[1]):
                invalid.append(f"threshold must be between {self.valid_thresholds[0]}-{self.valid_thresholds[1]}, got {params[param]}")
        
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
    
    def collect_parameters(self, message: str, analysis_type: str, existing_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """매개변수 수집 메인 메서드"""
        if existing_params is None:
            existing_params = {}
        
        # 새로 추출된 매개변수
        extracted = self._extract_parameters(message, analysis_type, existing_params)
        
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
        questions = []
        
        for param in missing_params:
            if param == "year":
                questions.append("어떤 연도로 분석하시겠습니까? (예: 2020, 2018)")
            elif param == "threshold":
                questions.append("해수면 상승 임계값을 몇 미터로 설정하시겠습니까? (예: 2.0m, 1.5m)")
            elif param == "location":
                questions.append("어떤 도시나 지역을 분석하시겠습니까? (예: Jakarta, Seoul)")
            elif param == "method":
                questions.append("어떤 토픽 모델링 방법을 사용하시겠습니까? (lda, nmf, bertopic)")
            elif param == "n_topics":
                questions.append("몇 개의 토픽으로 분석하시겠습니까? (예: 5, 10)")
        
        if len(questions) == 1:
            return questions[0]
        elif len(questions) == 2:
            return f"{questions[0]} 그리고 {questions[1]}"
        else:
            return f"{', '.join(questions[:-1])}, 그리고 {questions[-1]}"
