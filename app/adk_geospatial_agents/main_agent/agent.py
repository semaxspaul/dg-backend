"""
Main Coordinator Agent - ADK Standard
"""

import os
import asyncio
from datetime import date
from typing import Dict, Any, Optional
from collections import defaultdict

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_artifacts
from google.genai import types

from .prompts import get_main_agent_instruction, get_global_instruction
from .tools import (
    call_sea_level_agent,
    call_urban_agent, 
    call_infrastructure_agent,
    call_topic_modeling_agent,
    collect_parameters,
    detect_analysis_intent
)
from ..shared.utils.parameter_collector import parameter_collector
from ..shared.utils.bbox_utils import calculate_bbox, get_standard_buffer

date_today = date.today()

def setup_before_agent_call(callback_context: CallbackContext):
    """에이전트 호출 전 설정"""
    # 사용자별 상태 초기화
    if "user_states" not in callback_context.state:
        callback_context.state["user_states"] = defaultdict(lambda: {
            "status": "idle",  # idle, collecting_parameters, awaiting_confirmation, analysis_in_progress
            "analysis_type": None,
            "collected_params": {},
            "conversation_context": []
        })
    
    # 현재 사용자 ID 설정 (실제로는 요청에서 가져와야 함)
    if "current_user_id" not in callback_context.state:
        callback_context.state["current_user_id"] = 1  # 기본값

async def process_user_message(message: str, user_id: int, callback_context: CallbackContext) -> Dict[str, Any]:
    """사용자 메시지를 처리하는 메인 로직"""
    # ADK 에이전트 호출 전 설정
    setup_before_agent_call(callback_context)
    
    user_states = callback_context.state["user_states"]
    user_state = user_states[user_id]
    
    print(f"🚀 [Main Agent] Processing message from user {user_id}: '{message[:50]}...'")
    
    # 대화 컨텍스트에 사용자 메시지 추가
    if "conversation_context" not in user_state:
        user_state["conversation_context"] = []
    
    user_state["conversation_context"].append({
        "role": "user",
        "content": message,
        "timestamp": "now"
    })
    
    # 상태별 처리
    if user_state["status"] == "collecting_parameters":
        return await handle_parameter_collection(message, user_id, user_state, callback_context)
    elif user_state["status"] == "awaiting_confirmation":
        return await handle_confirmation(message, user_id, user_state, callback_context)
    else:
        return await handle_new_request(message, user_id, user_state, callback_context)

async def handle_new_request(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """새로운 요청 처리"""
    print(f"🔍 [Main Agent] Analyzing new request...")
    
    # 분석 의도 감지
    try:
        intent_result = await detect_analysis_intent(message, callback_context)
        print(f"🔍 [Main Agent] Intent detection result: {intent_result}")
        analysis_type = intent_result.get("intent")
        
        print(f"🔍 [Main Agent] analysis_type value: '{analysis_type}' (type: {type(analysis_type)})")
        print(f"🔍 [Main Agent] analysis_type is truthy: {bool(analysis_type)}")
        
        if analysis_type:
            print(f"📊 [Main Agent] Detected analysis type: {analysis_type}")
            print(f"📊 [Main Agent] Entering analysis setup block...")
        else:
            print(f"❌ [Main Agent] No analysis intent detected")
    except Exception as e:
        print(f"❌ [Main Agent] Intent detection error: {str(e)}")
        import traceback
        traceback.print_exc()
        analysis_type = None
    
    # analysis_type이 있을 때만 매개변수 수집 진행
    if analysis_type:
        print(f"🔧 [Main Agent] Setting up parameter collection for {analysis_type}...")
        
        # 매개변수 수집 시작
        user_state["status"] = "collecting_parameters"
        user_state["analysis_type"] = analysis_type
        user_state["collected_params"] = {}
        
        print(f"🔧 [Main Agent] User state updated: {user_state}")
        
        # 매개변수 수집
        try:
            print(f"🔧 [Main Agent] Starting parameter collection...")
            param_result = await parameter_collector.collect_parameters(
                message, analysis_type, user_state["collected_params"]
            )
            print(f"🔧 [Main Agent] Parameter collection result: {param_result}")
        except Exception as e:
            print(f"❌ [Main Agent] Parameter collection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "message": "매개변수 수집 중 오류가 발생했습니다. 다시 시도해주세요.",
                "status": "error"
            }
        
        if param_result["needs_more_info"]:
            print(f"🔧 [Main Agent] More information needed, generating question...")
            missing_params = param_result["validation"]["missing"]
            print(f"🔧 [Main Agent] Missing params: {missing_params}")
            
            # Country를 먼저, 그 다음 City를 질문하는 순서로 변경
            if "country_name" in missing_params:
                question = "어떤 국가를 분석하시겠습니까? (예: South Korea, United States)"
            elif "city_name" in missing_params:
                question = "어떤 도시를 분석하시겠습니까? (예: Seoul, Busan, New York)"
            else:
                # 첫 번째 누락된 매개변수만 질문
                first_missing = missing_params[0]
                question = parameter_collector.generate_questions([first_missing], analysis_type)
            
            response_message = f"네, {analysis_type.replace('_', ' ')} 분석을 도와드리겠습니다! {question}"
            print(f"🔧 [Main Agent] Generated response: {response_message}")
            
            # 대화 컨텍스트에 AI 응답 추가
            user_state["conversation_context"].append({
                "role": "assistant",
                "content": response_message,
                "timestamp": "now"
            })
            
            return {
                "message": response_message,
                "analysis_type": analysis_type,
                "status": "collecting_parameters",
                "needs_clarification": True
            }
        else:
            print(f"🔧 [Main Agent] All parameters collected, executing analysis...")
            # 모든 매개변수가 수집됨 - 분석 실행
            return await execute_analysis(analysis_type, param_result["params"], user_id, user_state, callback_context)
    else:
        # 일반 대화
        return {
            "message": "안녕하세요! DataGround 지리공간 분석 시스템입니다. 어떤 분석을 도와드릴까요?\n\n지원하는 분석:\n- 해수면 상승 위험 분석\n- 도시 지역 분석\n- 인프라 노출 분석\n- 토픽 모델링 분석",
            "status": "general_chat"
        }

async def handle_parameter_collection(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """매개변수 수집 중 처리"""
    print(f"🔧 [Main Agent] Collecting parameters for {user_state['analysis_type']}...")
    
    analysis_type = user_state["analysis_type"]
    existing_params = user_state["collected_params"]
    
    # 매개변수 수집
    try:
        param_result = await parameter_collector.collect_parameters(
            message, analysis_type, existing_params
        )
        print(f"🔧 [Main Agent] Parameter collection result: {param_result}")
    except Exception as e:
        print(f"❌ [Main Agent] Parameter collection error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "message": "매개변수 수집 중 오류가 발생했습니다. 다시 시도해주세요.",
            "status": "error"
        }
    
    # 수집된 매개변수 업데이트
    user_state["collected_params"] = param_result["params"]
    
    # 정확한 매칭이 있으면 제안 메시지를 무시하고 계속 진행
    has_exact_match = any(key in param_result["params"] for key in ["city_name", "country_name"])
    
    # 제안 메시지가 있고 정확한 매칭이 없는 경우에만 처리
    if not has_exact_match and "suggestion_message" in param_result["params"]:
        return {
            "message": param_result["params"]["suggestion_message"],
            "analysis_type": analysis_type,
            "status": "collecting_parameters",
            "needs_clarification": True,
            "suggestion": True
        }
    
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
    all_collected = parameter_collector.are_all_parameters_collected(
        param_result["params"], analysis_type
    )
    
    print(f"🔍 [Main Agent] Parameter collection check: all_collected={all_collected}")
    print(f"🔍 [Main Agent] Current params: {param_result['params']}")
    print(f"🔍 [Main Agent] Validation result: {param_result['validation']}")
    
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
            question = parameter_collector.generate_questions([next_missing], analysis_type)
        
        return {
            "message": f"{confirmation_message}\n\n{question}",
            "analysis_type": analysis_type,
            "status": "collecting_parameters",
            "needs_clarification": True
        }
    else:
        # 모든 매개변수 수집 완료 - 사용자 확인 요청
        print(f"✅ [Main Agent] All parameters collected, requesting user confirmation...")
        user_state["status"] = "awaiting_confirmation"  # 확인 대기 상태로 변경
        
        return {
            "message": f"{confirmation_message}\n\n다음 정보가 맞습니까? (yes/no)",
            "analysis_type": analysis_type,
            "status": "awaiting_confirmation",
            "needs_clarification": True
        }

async def handle_confirmation(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """사용자 확인 처리"""
    print(f"❓ [Main Agent] Handling user confirmation...")
    
    message_lower = message.lower().strip()
    
    # 긍정적 응답 확인
    positive_responses = ['yes', 'y', '응', '그래', '맞아', '맞다', '맞습니다', '네', '좋아', 'ok', 'okay']
    negative_responses = ['no', 'n', '아니', '아니다', '아니요', '아닙니다', '틀렸', '다시', '취소']
    
    if any(response in message_lower for response in positive_responses):
        # 사용자 확인 - 분석 실행
        print(f"✅ [Main Agent] User confirmed, executing analysis...")
        user_state["status"] = "idle"  # 상태 리셋
        analysis_type = user_state["analysis_type"]
        collected_params = user_state["collected_params"]
        return await execute_analysis(analysis_type, collected_params, user_id, user_state, callback_context)
    
    elif any(response in message_lower for response in negative_responses):
        # 사용자 거부 - 처음부터 다시 시작
        print(f"🔄 [Main Agent] User rejected, restarting parameter collection...")
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

async def execute_analysis(analysis_type: str, params: Dict[str, Any], user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """실제 분석 실행"""
    print(f"🚀 [Main Agent] Executing {analysis_type} analysis with params: {params}")
    
    try:
        # 분석 요청 구성
        analysis_request = {
            "analysis_type": analysis_type,
            "parameters": params,
            "user_id": user_id
        }
        
        # 실제 GEE API 호출
        if analysis_type == "sea_level_rise":
            result = await call_sea_level_analysis_api(params)
        elif analysis_type == "urban_analysis":
            result = await call_urban_analysis_api(params)
        elif analysis_type == "infrastructure_analysis":
            result = await call_infrastructure_analysis_api(params)
        elif analysis_type == "topic_modeling":
            result = await call_topic_modeling_api(params)
        else:
            return {
                "message": f"지원하지 않는 분석 유형입니다: {analysis_type}",
                "status": "error"
            }
        
        # 대화 컨텍스트에 AI 응답 추가
        response_message = f"✅ **{analysis_type.replace('_', ' ').title()} 분석이 완료되었습니다!**\n\n"
        response_message += f"요청하신 매개변수:\n"
        response_message += f"- 연도: {params.get('year', 'N/A')}\n"
        response_message += f"- 임계값: {params.get('threshold', 'N/A')}m\n"
        response_message += f"- 도시: {params.get('city_name', 'N/A')}\n"
        response_message += f"- 국가: {params.get('country_name', 'N/A')}\n\n"
        response_message += f"결과가 대시보드에 표시되었습니다. 추가 질문이 있으신가요?"
        
        user_state["conversation_context"].append({
            "role": "assistant",
            "content": response_message,
            "timestamp": "now"
        })
        
        dashboard_updates = result.get("dashboard_updates", [])
        print(f"🔍 [Main Agent] Dashboard updates generated: {len(dashboard_updates)} items")
        print(f"🔍 [Main Agent] Dashboard updates content: {dashboard_updates}")
        
        return {
            "message": response_message,
            "status": "analysis_completed",
            "dashboard_updated": True,
            "dashboard_updates": dashboard_updates,
            "analysis_results": result
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_message = f"❌ 분석 실행 중 예외가 발생했습니다: {str(e)}"
        
        user_state["conversation_context"].append({
            "role": "assistant",
            "content": error_message,
            "timestamp": "now"
        })
        
        return {
            "message": error_message,
            "status": "error"
        }

# Mock 분석 함수들 (실제 분석 로직 대신)
async def mock_sea_level_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 해수면 상승 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "sea_level_rise",
        "results": {
            "risk_level": "High",
            "affected_area": "15.2 km²",
            "population_at_risk": "45,000"
        },
        "dashboard_updates": [
            {"type": "map", "data": "sea_level_risk_map"},
            {"type": "chart", "data": "risk_distribution_chart"}
        ]
    }

async def mock_urban_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 도시 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "urban_analysis",
        "results": {
            "urban_growth_rate": "3.2%",
            "population_density": "2,450/km²",
            "built_up_area": "28.5 km²"
        },
        "dashboard_updates": [
            {"type": "map", "data": "urban_expansion_map"},
            {"type": "chart", "data": "growth_trends_chart"}
        ]
    }

async def mock_infrastructure_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 인프라 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "infrastructure_analysis",
        "results": {
            "exposed_infrastructure": "12 facilities",
            "risk_score": "7.8/10",
            "vulnerable_assets": "roads, bridges, power plants"
        },
        "dashboard_updates": [
            {"type": "map", "data": "infrastructure_exposure_map"},
            {"type": "chart", "data": "vulnerability_assessment_chart"}
        ]
    }

async def mock_topic_modeling_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 토픽 모델링 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "topic_modeling",
        "results": {
            "topics_found": 5,
            "main_topics": ["climate change", "urban planning", "infrastructure", "risk assessment", "policy"],
            "coherence_score": 0.85
        },
        "dashboard_updates": [
            {"type": "chart", "data": "topic_distribution_chart"},
            {"type": "table", "data": "topic_keywords_table"}
        ]
    }

# ADK Agent 생성
main_agent = Agent(
    model=os.getenv("MAIN_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="geospatial_analysis_coordinator",
    instruction=get_main_agent_instruction(),
    global_instruction=get_global_instruction(),
    sub_agents=[],  # 서브 에이전트들은 tools를 통해 호출
    tools=[
        call_sea_level_agent,
        call_urban_agent,
        call_infrastructure_agent,
        call_topic_modeling_agent,
        collect_parameters,
        detect_analysis_intent,
        load_artifacts
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)

# 실제 GEE API 호출 함수들
async def call_sea_level_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sea Level Rise 분석 API 호출"""
    try:
        import httpx
        
        # API 엔드포인트 URL
        base_url = "http://localhost:8000"  # FastAPI 서버 URL
        endpoint = "/analysis/sea-level-rise"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("sea_level_rise")
        bbox_params = calculate_bbox(coordinates, buffer)
        bbox_params["threshold"] = params.get("threshold", 2.0)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            dashboard_updates = [
                {
                    "type": "map_update",
                    "data": result.get("map_data", {}),
                    "center": [params.get("coordinates", {}).get("lng", 0), 
                             params.get("coordinates", {}).get("lat", 0)],
                    "zoom": 10
                },
                {
                    "type": "chart_update", 
                    "data": result.get("chart_data", {}),
                    "chart_type": "sea_level_rise"
                }
            ]
            
            print(f"🔍 [API Call] Sea Level Rise dashboard_updates created: {len(dashboard_updates)} items")
            print(f"🔍 [API Call] Dashboard updates content: {dashboard_updates}")
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": dashboard_updates
            }
    except Exception as e:
        print(f"❌ [API Call] Sea Level Rise API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_urban_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Urban Analysis API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/urban-area-comprehensive-stats"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("urban_analysis")
        bbox_params = calculate_bbox(coordinates, buffer)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "map_update",
                        "data": result.get("map_data", {}),
                        "center": [params.get("coordinates", {}).get("lng", 0), 
                                 params.get("coordinates", {}).get("lat", 0)],
                        "zoom": 10
                    },
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "urban_analysis"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Urban Analysis API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_infrastructure_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Infrastructure Analysis API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/infrastructure-exposure"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("infrastructure_analysis")
        bbox_params = calculate_bbox(coordinates, buffer)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "map_update",
                        "data": result.get("map_data", {}),
                        "center": [params.get("coordinates", {}).get("lng", 0), 
                                 params.get("coordinates", {}).get("lat", 0)],
                        "zoom": 10
                    },
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "infrastructure_exposure"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Infrastructure Analysis API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_topic_modeling_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Topic Modeling API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/topic-modeling"
        
        # 요청 데이터 구성 (POST 요청)
        request_data = {
            "year": params.get("year"),
            "method": params.get("method", "lda"),
            "topics": params.get("topics", 5)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}{endpoint}", json=request_data)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "topic_modeling"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Topic Modeling API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }
