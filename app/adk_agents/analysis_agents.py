"""
분석 전문 ADK 에이전트들
"""

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
from .tools import sea_level_risk_tool, urban_analysis_tool, infrastructure_tool, topic_modeling_tool

class SeaLevelRiseAgent:
    """해수면 상승 위험 분석 전문 에이전트"""
    
    def __init__(self):
        self.agent = LlmAgent(
            name="sea_level_rise_agent",
            model="gemini-2.0-flash-exp",
            description="해수면 상승 위험 분석을 수행하는 전문 에이전트",
            instruction="""
            당신은 해수면 상승 위험 분석 전문가입니다.
            
            주요 기능:
            1. 해수면 상승 위험 분석 실행
            2. 분석 결과 해석 및 시각화
            3. 위험 지역 식별 및 권고사항 제공
            4. 인구 노출 분석 포함
            
            분석 매개변수:
            - threshold: 해수면 상승 임계값 (미터)
            - year: 분석 연도
            - location: 분석 지역 (도시명 또는 좌표)
            
            항상 정확하고 이해하기 쉬운 분석 결과를 제공하세요.
            """,
            tools=[sea_level_risk_tool]
        )

class UrbanAnalysisAgent:
    """도시 지역 분석 전문 에이전트"""
    
    def __init__(self):
        self.agent = LlmAgent(
            name="urban_analysis_agent",
            model="gemini-2.0-flash-exp", 
            description="도시 지역 분석을 수행하는 전문 에이전트",
            instruction="""
            당신은 도시 지역 분석 전문가입니다.
            
            주요 기능:
            1. 도시 확장 분석
            2. 도시 지역 통계 분석
            3. 시계열 도시 발전 분석
            4. 도시-위험 결합 분석
            
            분석 매개변수:
            - year: 분석 연도
            - threshold: 도시 지역 임계값
            - location: 분석 지역
            
            도시 발전 패턴과 위험 요소를 종합적으로 분석하세요.
            """,
            tools=[urban_analysis_tool]
        )

class InfrastructureAgent:
    """인프라 노출 분석 전문 에이전트"""
    
    def __init__(self):
        self.agent = LlmAgent(
            name="infrastructure_agent",
            model="gemini-2.0-flash-exp",
            description="인프라 노출 분석을 수행하는 전문 에이전트", 
            instruction="""
            당신은 인프라 노출 분석 전문가입니다.
            
            주요 기능:
            1. 인프라 시설의 해수면 상승 위험 분석
            2. 중요 인프라 보호 우선순위 제시
            3. 인프라 복원력 평가
            4. 위험 완화 방안 제안
            
            분석 매개변수:
            - year: 분석 연도
            - threshold: 해수면 상승 임계값
            - location: 분석 지역
            
            인프라 보호를 위한 실용적인 권고사항을 제공하세요.
            """,
            tools=[infrastructure_tool]
        )

class TopicModelingAgent:
    """토픽 모델링 분석 전문 에이전트"""
    
    def __init__(self):
        self.agent = LlmAgent(
            name="topic_modeling_agent",
            model="gemini-2.0-flash-exp",
            description="토픽 모델링 분석을 수행하는 전문 에이전트",
            instruction="""
            당신은 토픽 모델링 분석 전문가입니다.
            
            주요 기능:
            1. 텍스트 데이터의 토픽 추출
            2. 토픽별 키워드 분석
            3. 문서-토픽 분포 분석
            4. 토픽 시각화 및 해석
            
            분석 매개변수:
            - method: 토픽 모델링 방법 (lda, nmf, bertopic)
            - n_topics: 토픽 수
            - file_path: 분석할 파일 경로
            
            텍스트 데이터의 숨겨진 패턴을 발견하고 해석하세요.
            """,
            tools=[topic_modeling_tool]
        )
