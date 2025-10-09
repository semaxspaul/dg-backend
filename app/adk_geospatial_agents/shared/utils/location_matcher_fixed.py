"""
Location Matcher - 개선된 버전
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import difflib
import re

class LocationMatcher:
    """위치 매칭을 위한 클래스"""
    
    def __init__(self, csv_path: str = "worldcities.csv"):
        self.csv_path = csv_path
        self.cities_df = None
        self.countries = set()
        self._load_data()
    
    def _load_data(self):
        """CSV 데이터 로드"""
        try:
            self.cities_df = pd.read_csv(self.csv_path)
            # NaN 값 제거 및 문자열 타입 확인
            self.cities_df = self.cities_df.dropna(subset=['city', 'country'])
            self.cities_df['city'] = self.cities_df['city'].astype(str)
            self.cities_df['country'] = self.cities_df['country'].astype(str)
            
            # 국가 목록 생성
            self.countries = set(self.cities_df['country'].str.lower().unique())
            
            print(f"✅ [LocationMatcher] Loaded {len(self.cities_df)} cities from {len(self.countries)} countries")
        except Exception as e:
            print(f"❌ [LocationMatcher] Error loading data: {e}")
            self.cities_df = pd.DataFrame()
            self.countries = set()
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """문자열 유사도 계산 (edit distance 기반)"""
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _find_best_match(self, target: str, candidates: List[str], threshold: float = 0.8) -> tuple:
        """가장 유사한 후보 찾기"""
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = self._calculate_similarity(target, candidate)
            if score > best_score and score >= threshold:
                best_match = candidate
                best_score = score
        
        return best_match, best_score
    
    def find_city(self, city_name: str, threshold: float = 0.8) -> Dict[str, Any]:
        """도시명으로 검색하고 매칭 결과 반환"""
        if not city_name or self.cities_df.empty:
            return {"found": False, "message": "No city data available"}
        
        city_lower = city_name.lower().strip()
        print(f"🔍 [LocationMatcher] Searching for city: '{city_lower}' with threshold: {threshold}")
        
        # 정확한 매칭 시도
        exact_matches = self.cities_df[self.cities_df['city'].str.lower() == city_lower]
        if not exact_matches.empty:
            row = exact_matches.iloc[0]
            print(f"✅ [LocationMatcher] Found exact match for city: {city_name.title()}")
            return {
                "found": True,
                "exact_match": True,
                "city": row['city'],
                "country": row['country'],
                "coordinates": {"lat": row['lat'], "lng": row['lng']}
            }
        
        # 유사한 도시 검색
        print(f"🔍 [LocationMatcher] Searching similar cities in {len(self.cities_df)} cities")
        best_match, best_score = self._find_best_match(city_lower, self.cities_df['city'].str.lower().tolist(), threshold)
        
        print(f"🔍 [LocationMatcher] Best match: '{best_match}' with score: {best_score:.3f}")
        
        if best_match:
            row = self.cities_df[self.cities_df['city'].str.lower() == best_match].iloc[0]
            return {
                "found": True,
                "exact_match": False,
                "city": row['city'],
                "country": row['country'],
                "coordinates": {"lat": row['lat'], "lng": row['lng']},
                "suggested_city": best_match.title(),
                "suggested_country": row['country'],
                "similarity_score": best_score,
                "message": f"혹시 '{best_match.title()}, {row['country']}'을 말씀하신 건가요?"
            }
        
        return {"found": False, "message": f"'{city_name}'에 해당하는 도시를 찾을 수 없습니다. 다른 도시명을 시도해보세요."}
    
    def find_country(self, country_name: str, threshold: float = 0.8) -> Dict[str, Any]:
        """국가명으로 검색하고 매칭 결과 반환"""
        if not country_name or self.cities_df.empty:
            return {"found": False, "message": "No country data available"}
        
        country_lower = country_name.lower().strip()
        print(f"🔍 [LocationMatcher] Searching for country: '{country_lower}' with threshold: {threshold}")
        
        # 특별 매핑 처리
        special_mappings = {
            "south korea": "korea, south",
            "north korea": "korea, north",
            "united states": "united states of america",
            "usa": "united states of america",
            "uk": "united kingdom",
            "united kingdom": "united kingdom"
        }
        
        if country_lower in special_mappings:
            country_lower = special_mappings[country_lower]
            print(f"🔍 [LocationMatcher] Mapped to: '{country_lower}'")
        
        if country_lower in self.countries:
            country_cities = self.cities_df[self.cities_df['country'].str.lower() == country_lower].head(5)
            cities_list = [{"city": row['city'], "lat": row['lat'], "lng": row['lng']} for _, row in country_cities.iterrows()]
            print(f"✅ [LocationMatcher] Found exact match for country: {country_name.title()}")
            return {
                "found": True,
                "exact_match": True,
                "country": country_name.title(),
                "cities": cities_list
            }
        else:
            # 유사한 국가 검색 (edit distance 기반)
            print(f"🔍 [LocationMatcher] Searching similar countries in {len(self.countries)} countries")
            best_match, best_score = self._find_best_match(country_lower, list(self.countries), threshold)
            
            print(f"🔍 [LocationMatcher] Best match: '{best_match}' with score: {best_score:.3f}")
            
            if best_match:
                country_cities = self.cities_df[self.cities_df['country'].str.lower() == best_match].head(5)
                cities_list = [{"city": row['city'], "lat": row['lat'], "lng": row['lng']} for _, row in country_cities.iterrows()]
                return {
                    "found": True,
                    "exact_match": False,
                    "country": best_match.title(),
                    "cities": cities_list,
                    "suggested_country": best_match.title(),
                    "similarity_score": best_score,
                    "message": f"혹시 '{best_match.title()}'을 말씀하신 건가요?"
                }
        
        return {"found": False, "message": f"'{country_name}'에 해당하는 국가를 찾을 수 없습니다. 다른 국가명을 시도해보세요."}
    
    def extract_location_from_message(self, message: str, search_type: str = "auto") -> Dict[str, Any]:
        """메시지에서 위치 정보 추출
        
        Args:
            message: 입력 메시지
            search_type: "city", "country", "auto" 중 하나
        """
        if not message or self.cities_df.empty:
            return {"found": False, "message": "No location data available"}
        
        message = message.strip()
        print(f"🔍 [LocationMatcher] extract_location_from_message called with: '{message}' (search_type: {search_type})")
        
        # 부정적 응답 처리 ("No," 제거)
        negative_words = ["no,", "아니", "아니요", "아니다"]
        for word in negative_words:
            if message.lower().startswith(word):
                message = message[len(word):].strip()
                print(f"🔍 [LocationMatcher] After negative word processing: '{message}'")
                break
        
        # 위치 정보가 아닌 일반적인 단어들은 무시
        non_location_words = {
            '해수면', '상승', '분석', '위험', '도시', '지역', '인프라', '노출', 
            '토픽', '모델링', 'year', '년', '미터', 'meter', 'm', 'threshold',
            'yes', 'no', '응', '아니', '맞아', '맞다', 'ok', 'okay'
        }
        
        if message.lower() in non_location_words:
            print(f"🔍 [LocationMatcher] Ignoring non-location word: '{message.lower()}'")
            return {"found": False, "message": "위치 정보가 아닙니다."}
        
        # 쉼표로 구분된 경우 (예: "Seoul, South Korea")
        if ',' in message:
            parts = [part.strip() for part in message.split(',')]
            print(f"🔍 [LocationMatcher] Comma-separated parts: {parts}")
            
            # search_type에 따라 검색 우선순위 결정
            if search_type == "city":
                # 도시 우선 검색
                for part in parts:
                    if part.lower() not in non_location_words and len(part) > 2:
                        print(f"🔍 [LocationMatcher] Trying city search for part: '{part}'")
                        city_result = self.find_city(part)
                        if city_result["found"]:
                            return city_result
            elif search_type == "country":
                # 국가 우선 검색
                for part in parts:
                    if part.lower() not in non_location_words and len(part) > 2:
                        print(f"🔍 [LocationMatcher] Trying country search for part: '{part}'")
                        country_result = self.find_country(part)
                        if country_result["found"]:
                            return country_result
            else:
                # auto: 도시 먼저, 그 다음 국가
                for part in parts:
                    if part.lower() not in non_location_words and len(part) > 2:
                        print(f"🔍 [LocationMatcher] Trying city search for part: '{part}'")
                        city_result = self.find_city(part)
                        if city_result["found"]:
                            return city_result
                
                for part in parts:
                    if part.lower() not in non_location_words and len(part) > 2:
                        print(f"🔍 [LocationMatcher] Trying country search for part: '{part}'")
                        country_result = self.find_country(part)
                        if country_result["found"]:
                            return country_result
        else:
            # 단일 텍스트 처리
            print(f"🔍 [LocationMatcher] Single text processing for: '{message}'")
            
            if search_type == "city":
                # 도시만 검색
                return self.find_city(message)
            elif search_type == "country":
                # 국가만 검색
                return self.find_country(message)
            else:
                # auto: 도시 먼저, 그 다음 국가
                city_result = self.find_city(message)
                if city_result["found"]:
                    return city_result
                
                country_result = self.find_country(message)
                if country_result["found"]:
                    return country_result
        
        return {"found": False, "message": "위치 정보를 찾을 수 없습니다."}

# 전역 인스턴스 생성
location_matcher = LocationMatcher()
