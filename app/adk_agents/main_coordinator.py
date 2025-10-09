"""
메인 코디네이터 ADK 에이전트
"""

from typing import Dict, Any, Optional
try:
    from google.adk.agents import LlmAgent
except ImportError:
    # Fallback: 간단한 LlmAgent 클래스 정의
    class LlmAgent:
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'agent')
            self.model = kwargs.get('model', 'gpt-4')
            self.description = kwargs.get('description', '')
            self.instruction = kwargs.get('instruction', '')
            self.tools = kwargs.get('tools', [])
            self.sub_agents = kwargs.get('sub_agents', [])
from .analysis_agents import SeaLevelRiseAgent, UrbanAnalysisAgent, InfrastructureAgent, TopicModelingAgent
from .parameter_collector import ParameterCollectorAgent

class MainCoordinatorAgent:
    """전체 시스템을 조율하는 메인 에이전트"""
    
    def __init__(self):
        # 서브 에이전트들 초기화
        self.sea_level_agent = SeaLevelRiseAgent()
        self.urban_agent = UrbanAnalysisAgent()
        self.infrastructure_agent = InfrastructureAgent()
        self.topic_modeling_agent = TopicModelingAgent()
        self.parameter_collector = ParameterCollectorAgent()
        
        # 사용자별 상태 관리
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
        # 메인 코디네이터 에이전트
        self.agent = LlmAgent(
            name="main_coordinator",
            model="gemini-2.0-flash-exp",
            description="지리공간 분석 요청을 감지하고 적절한 전문 에이전트에게 위임하는 메인 코디네이터",
            instruction="""
            당신은 DataGround 지리공간 분석 시스템의 메인 코디네이터입니다.
            
            주요 역할:
            1. 사용자 요청 분석 및 의도 파악
            2. 적절한 전문 에이전트에게 작업 위임
            3. 매개변수 수집 상태 관리
            4. 분석 결과 통합 및 사용자에게 전달
            
            지원하는 분석 유형:
            - sea_level_rise: 해수면 상승 위험 분석
            - urban_analysis: 도시 지역 분석  
            - infrastructure_analysis: 인프라 노출 분석
            - topic_modeling: 토픽 모델링 분석
            
            위임 규칙:
            - "sea level rise", "해수면 상승" → sea_level_rise_agent
            - "urban", "도시", "urban area" → urban_analysis_agent
            - "infrastructure", "인프라", "exposure" → infrastructure_agent
            - "topic modeling", "토픽", "text analysis" → topic_modeling_agent
            
            매개변수가 부족한 경우 parameter_collector에게 위임하여 추가 정보 수집
            
            항상 사용자에게 친근하고 도움이 되는 응답을 제공하세요.
            """,
            sub_agents=[
                self.sea_level_agent.agent,
                self.urban_agent.agent, 
                self.infrastructure_agent.agent,
                self.topic_modeling_agent.agent,
                self.parameter_collector.agent
            ]
        )
    
    def process_message(self, message: str, user_id: int, chat_history: list = None) -> Dict[str, Any]:
        """사용자 메시지 처리"""
        print(f"🚀 [ADK] Processing message from user {user_id}: '{message[:50]}...'")
        
        # 사용자 상태 초기화 (없는 경우)
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "status": "idle",
                "analysis_type": None,
                "collected_params": {},
                "conversation_context": []
            }
        
        user_state = self.user_states[user_id]
        
        # 대화 컨텍스트 업데이트
        if chat_history:
            user_state["conversation_context"] = chat_history[-5:]  # 최근 5개 메시지만 유지
        
        # 상태별 처리
        if user_state["status"] == "collecting_parameters":
            return self._handle_parameter_collection(message, user_id, user_state)
        elif user_state["status"] == "awaiting_confirmation":
            return self._handle_confirmation(message, user_id, user_state)
        else:
            return self._handle_new_request(message, user_id, user_state)
    
    def _handle_new_request(self, message: str, user_id: int, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """새로운 요청 처리"""
        print(f"🔍 [ADK] Analyzing new request...")
        
        # 의도 분석
        analysis_type = self._detect_analysis_intent(message)
        
        if analysis_type:
            print(f"📊 [ADK] Detected analysis type: {analysis_type}")
            
            # 매개변수 수집 시작
            user_state["status"] = "collecting_parameters"
            user_state["analysis_type"] = analysis_type
            user_state["collected_params"] = {}
            
            # 매개변수 수집
            param_result = self.parameter_collector.collect_parameters(
                message, analysis_type, user_state["collected_params"]
            )
            
            if param_result["needs_more_info"]:
                missing_params = param_result["validation"]["missing"]
                # Country를 먼저, 그 다음 City를 질문하는 순서로 변경
                if "country_name" in missing_params:
                    question = "어떤 국가를 분석하시겠습니까? (예: South Korea, United States)"
                elif "city_name" in missing_params:
                    question = "어떤 도시를 분석하시겠습니까? (예: Seoul, Busan, New York)"
                else:
                    # 첫 번째 누락된 매개변수만 질문
                    first_missing = missing_params[0]
                    question = self.parameter_collector.generate_questions([first_missing], analysis_type)
                
                return {
                    "message": f"네, {analysis_type.replace('_', ' ')} 분석을 도와드리겠습니다! {question}",
                    "analysis_type": analysis_type,
                    "status": "collecting_parameters",
                    "needs_clarification": True
                }
            else:
                # 모든 매개변수가 수집됨 - 분석 실행
                return self._execute_analysis(analysis_type, param_result["params"], user_id, user_state)
        else:
            # 일반 대화
            return {
                "message": "안녕하세요! DataGround 지리공간 분석 시스템입니다. 어떤 분석을 도와드릴까요?\n\n지원하는 분석:\n- 해수면 상승 위험 분석\n- 도시 지역 분석\n- 인프라 노출 분석\n- 토픽 모델링 분석",
                "status": "general_chat"
            }
    
    def _handle_parameter_collection(self, message: str, user_id: int, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """매개변수 수집 중 처리"""
        print(f"🔧 [ADK] Collecting parameters for {user_state['analysis_type']}...")
        
        analysis_type = user_state["analysis_type"]
        existing_params = user_state["collected_params"]
        
        # 매개변수 수집
        param_result = self.parameter_collector.collect_parameters(
            message, analysis_type, existing_params
        )
        
        # 수집된 매개변수 업데이트
        user_state["collected_params"] = param_result["params"]
        
        # 위치 정보 제안이 있는 경우 처리
        if "suggestion_message" in param_result["params"]:
            return {
                "message": param_result["params"]["suggestion_message"],
                "analysis_type": analysis_type,
                "status": "collecting_parameters",
                "needs_clarification": True,
                "suggestion": True
            }
        
        # 위치 정보 오류가 있는 경우는 무시하고 정상적인 매개변수 수집 과정 진행
        # (location_error는 단순히 위치 정보가 없다는 의미이므로 오류가 아님)
        
        # 수집된 정보 확인 메시지 생성
        collected = user_state["collected_params"]
        country = collected.get("country_name", "None")
        city = collected.get("city_name", "None") 
        year = collected.get("year", "None")
        threshold = collected.get("threshold", "None")
        
        if threshold != "None":
            threshold = f"{threshold}m"
        
        confirmation_message = f"감사합니다! 다음 정보를 받았습니다:\n"
        confirmation_message += f"Country: {country}\n"
        confirmation_message += f"City: {city}\n" 
        confirmation_message += f"Year: {year}\n"
        confirmation_message += f"Sea-level: {threshold}"
        
        # 모든 매개변수가 수집되었는지 확인
        all_collected = self.parameter_collector.are_all_parameters_collected(
            param_result["params"], analysis_type
        )
        
        print(f"🔍 [ADK] Parameter collection check: all_collected={all_collected}")
        print(f"🔍 [ADK] Current params: {param_result['params']}")
        print(f"🔍 [ADK] Validation result: {param_result['validation']}")
        
        if not all_collected:
            # 아직 누락된 매개변수가 있음
            missing_params = param_result["validation"]["missing"]
            # Country를 먼저, 그 다음 City를 질문하는 순서로 변경
            if "country_name" in missing_params:
                question = "어떤 국가를 분석하시겠습니까? (예: South Korea, United States)"
            elif "city_name" in missing_params:
                question = "어떤 도시를 분석하시겠습니까? (예: Seoul, Busan, New York)"
            else:
                # 다음 누락된 매개변수만 질문
                next_missing = missing_params[0]
                question = self.parameter_collector.generate_questions([next_missing], analysis_type)
            
            return {
                "message": f"{confirmation_message}\n\n{question}",
                "analysis_type": analysis_type,
                "status": "collecting_parameters",
                "needs_clarification": True
            }
        else:
            # 모든 매개변수 수집 완료 - 사용자 확인 요청
            print(f"✅ [ADK] All parameters collected, requesting user confirmation...")
            user_state["status"] = "awaiting_confirmation"  # 확인 대기 상태로 변경
            
            return {
                "message": f"{confirmation_message}\n\n다음 정보가 맞습니까? (yes/no)",
                "analysis_type": analysis_type,
                "status": "awaiting_confirmation",
                "needs_clarification": True
            }
    
    def _handle_confirmation(self, message: str, user_id: int, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 확인 처리"""
        print(f"❓ [ADK] Handling user confirmation...")
        
        message_lower = message.lower().strip()
        
        # 긍정적 응답 확인
        positive_responses = ['yes', 'y', '응', '그래', '맞아', '맞다', '맞습니다', '네', '좋아', 'ok', 'okay']
        negative_responses = ['no', 'n', '아니', '아니다', '아니요', '아닙니다', '틀렸', '다시', '취소']
        
        if any(response in message_lower for response in positive_responses):
            # 사용자 확인 - 분석 실행
            print(f"✅ [ADK] User confirmed, executing analysis...")
            user_state["status"] = "idle"  # 상태 리셋
            analysis_type = user_state["analysis_type"]
            collected_params = user_state["collected_params"]
            return self._execute_analysis(analysis_type, collected_params, user_id, user_state)
        
        elif any(response in message_lower for response in negative_responses):
            # 사용자 거부 - 처음부터 다시 시작
            print(f"🔄 [ADK] User rejected, restarting parameter collection...")
            user_state["status"] = "collecting_parameters"
            user_state["collected_params"] = {}  # 수집된 매개변수 초기화
            
            analysis_type = user_state["analysis_type"]
            return {
                "message": f"알겠습니다! {analysis_type.replace('_', ' ')} 분석을 다시 시작하겠습니다. 어떤 연도로 분석하시겠습니까? (예: 2020, 2018)",
                "analysis_type": analysis_type,
                "status": "collecting_parameters",
                "needs_clarification": True
            }
        
        else:
            # 명확하지 않은 응답 - 다시 확인 요청
            collected = user_state["collected_params"]
            country = collected.get("country_name", "None")
            city = collected.get("city_name", "None") 
            year = collected.get("year", "None")
            threshold = collected.get("threshold", "None")
            
            if threshold != "None":
                threshold = f"{threshold}m"
            
            confirmation_message = f"감사합니다! 다음 정보를 받았습니다:\n"
            confirmation_message += f"Country: {country}\n"
            confirmation_message += f"City: {city}\n" 
            confirmation_message += f"Year: {year}\n"
            confirmation_message += f"Sea-level: {threshold}"
            
            return {
                "message": f"{confirmation_message}\n\n다음 정보가 맞습니까? (yes/no)",
                "analysis_type": user_state["analysis_type"],
                "status": "awaiting_confirmation",
                "needs_clarification": True
            }
    
    def _detect_analysis_intent(self, message: str) -> Optional[str]:
        """메시지에서 분석 의도 감지"""
        message_lower = message.lower()
        
        # 키워드 기반 의도 감지
        if any(keyword in message_lower for keyword in ["sea level", "해수면", "slr"]):
            return "sea_level_rise"
        elif any(keyword in message_lower for keyword in ["urban", "도시", "city"]):
            return "urban_analysis"
        elif any(keyword in message_lower for keyword in ["infrastructure", "인프라", "exposure"]):
            return "infrastructure_analysis"
        elif any(keyword in message_lower for keyword in ["topic modeling", "토픽", "text analysis"]):
            return "topic_modeling"
        
        return None
    
    def _execute_analysis(self, analysis_type: str, params: Dict[str, Any], user_id: int, user_state: Dict[str, Any]) -> Dict[str, Any]:
        """분석 실행"""
        print(f"🚀 [ADK] Executing {analysis_type} analysis with params: {params}")
        
        try:
            # 분석 유형에 따른 에이전트 선택
            if analysis_type == "sea_level_rise":
                agent = self.sea_level_agent.agent
            elif analysis_type == "urban_analysis":
                agent = self.urban_agent.agent
            elif analysis_type == "infrastructure_analysis":
                agent = self.infrastructure_agent.agent
            elif analysis_type == "topic_modeling":
                agent = self.topic_modeling_agent.agent
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            # 분석 실행 (실제로는 ADK의 에이전트 실행 로직 사용)
            # 여기서는 시뮬레이션
            result = {
                "status": "completed",
                "analysis_type": analysis_type,
                "parameters": params,
                "message": f"✅ {analysis_type.replace('_', ' ')} 분석이 완료되었습니다!\n\n사용된 매개변수:\n" + 
                          "\n".join([f"- {k}: {v}" for k, v in params.items()])
            }
            
            print(f"✅ [ADK] Analysis completed successfully")
            return result
            
        except Exception as e:
            print(f"❌ [ADK] Analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": f"분석 중 오류가 발생했습니다: {str(e)}",
                "analysis_type": analysis_type
            }
