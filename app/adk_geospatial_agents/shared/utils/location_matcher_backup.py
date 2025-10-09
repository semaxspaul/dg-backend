"""
ADK Location Matcher Utility
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Optional
import difflib

class LocationMatcher:
    """위치 매칭을 위한 유틸리티 클래스"""
    
    def __init__(self, csv_path: str = "worldcities.csv"):
        self.csv_path = csv_path
        self.cities_df: pd.DataFrame = pd.DataFrame()
        self.countries = set()
        self.cities = set()
        self.city_country_mapping = {}
        self._load_data()

    def _load_data(self):
        """worldcities.csv 데이터 로드"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_file_path = os.path.join(current_dir, "..", "..", "..", "..", self.csv_path)
            
            self.cities_df = pd.read_csv(csv_file_path)
            
            # NaN 값 제거 및 문자열 타입 확인
            self.cities_df = self.cities_df.dropna(subset=['city', 'country'])
            
            # 국가 목록 생성
            self.countries = set()
            for country in self.cities_df['country'].unique():
                if pd.notna(country) and isinstance(country, str):
                    self.countries.add(country.lower())
            
            # 도시 목록 및 매핑 생성
            self.cities = set()
            for _, row in self.cities_df.iterrows():
                if pd.notna(row['city']) and isinstance(row['city'], str):
                    self.cities.add(row['city'].lower())
                    self.city_country_mapping[row['city'].lower()] = row['country']
                
                if pd.notna(row['city_ascii']) and isinstance(row['city_ascii'], str):
                    self.cities.add(row['city_ascii'].lower())
                    self.city_country_mapping[row['city_ascii'].lower()] = row['country']
            
            print(f"✅ [LocationMatcher] Loaded {len(self.cities_df)} cities from {len(self.countries)} countries")
            
        except Exception as e:
            print(f"❌ [LocationMatcher] Error loading worldcities.csv: {str(e)}")
            import traceback
            traceback.print_exc()
            self.cities_df = pd.DataFrame()
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """두 문자열의 유사도를 계산 (0.0 ~ 1.0)"""
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _find_best_match(self, query: str, candidates: List[str], threshold: float = 0.8) -> Tuple[str, float]:
        """후보들 중에서 가장 유사한 문자열을 찾아 반환"""
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = self._calculate_similarity(query, candidate)
            if score > best_score and score >= threshold:
                best_match = candidate
                best_score = score
        
        return best_match, best_score

    def find_city(self, city_name: str, threshold: float = 0.8) -> Dict[str, any]:
        """도시명으로 검색하고 매칭 결과 반환"""
        if not city_name or self.cities_df.empty:
            return {"found": False, "message": "No city data available"}
        
        city_lower = city_name.lower().strip()
        
        if city_lower in self.cities:
            row = self.cities_df[(self.cities_df['city'].str.lower() == city_lower) | (self.cities_df['city_ascii'].str.lower() == city_lower)].iloc[0]
            return {
                "found": True,
                "exact_match": True,
                "city": row['city'],
                "country": row['country'],
                "coordinates": {"lat": row['lat'], "lng": row['lng']}
            }
        else:
            # 유사한 도시 검색 (edit distance 기반)
            best_match, best_score = self._find_best_match(city_lower, list(self.cities), threshold)
            if best_match:
                row = self.cities_df[(self.cities_df['city'].str.lower() == best_match) | (self.cities_df['city_ascii'].str.lower() == best_match)].iloc[0]
                return {
                    "found": True,
                    "exact_match": False,
                    "city": best_match.title(),
                    "country": row['country'],
                    "coordinates": {"lat": row['lat'], "lng": row['lng']},
                    "suggested_city": best_match.title(),
                    "suggested_country": row['country'],
                    "similarity_score": best_score,
                    "message": f"혹시 '{best_match.title()}, {row['country']}'을 말씀하신 건가요?"
                }
        
        return {"found": False, "message": f"'{city_name}'에 해당하는 도시를 찾을 수 없습니다. 다른 도시명을 시도해보세요."}

    def find_country(self, country_name: str, threshold: float = 0.8) -> Dict[str, any]:
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
        """메시지에서 위치 정보 추출"""
        print(f"🔍 [LocationMatcher] extract_location_from_message called with: '{message}'")
        message_lower = message.lower().strip()
        
        # 부정어가 포함된 경우 처리 (예: "No, Busan" -> "Busan"만 추출)
        negative_words = ['no', '아니', 'not', '아니다']
        for neg_word in negative_words:
            if message_lower.startswith(neg_word + ','):
                message = message.split(',', 1)[1].strip()
                message_lower = message.lower()
                print(f"🔍 [LocationMatcher] After negative word processing: '{message_lower}'")
                break
        
        # 위치 정보가 아닌 일반적인 단어들은 무시
        non_location_words = {
            '해수면', '상승', '분석', '위험', '도시', '지역', '인프라', '노출', 
            '토픽', '모델링', 'year', '년', '미터', 'meter', 'm', 'threshold',
            'yes', 'no', '응', '아니', '맞아', '맞다', 'ok', 'okay'
        }
        
        if message_lower in non_location_words:
            print(f"🔍 [LocationMatcher] Ignoring non-location word: '{message_lower}'")
            return {
                "type": "none",
                "result": {"found": False, "message": "위치 정보가 아닙니다."},
                "original_text": message
            }
        
        # 정규식을 사용하여 위치 정보 추출
        import re
        
        # "in Seoul, South Korea" 패턴 추출
        location_pattern = r'in\s+([^,]+)(?:,\s*([^,\s]+))?'
        match = re.search(location_pattern, message_lower)
        if match:
            city_part = match.group(1).strip()
            country_part = match.group(2).strip() if match.group(2) else None
            
            print(f"🔍 [LocationMatcher] Extracted from pattern - City: '{city_part}', Country: '{country_part}'")
            
            # 도시 검색
            if city_part and city_part not in non_location_words:
                city_result = self.find_city(city_part)
                if city_result["found"] and city_result["exact_match"]:
                    return {
                        "type": "city",
                        "result": city_result,
                        "original_text": city_part
                    }
            
            # 국가 검색 (더 정확한 패턴으로)
            if country_part and country_part not in non_location_words:
                # "South Korea for 2020" -> "South Korea"만 추출
                country_clean = re.sub(r'\s+(for|with|in|at|on|by)\s+.*', '', country_part).strip()
                if country_clean:
                    country_result = self.find_country(country_clean)
                    if country_result["found"] and country_result["exact_match"]:
                        return {
                            "type": "country",
                            "result": country_result,
                            "original_text": country_clean
                        }
        
        # 쉼표로 구분된 경우 처리 (예: "Korea, Busan")
        if ',' in message:
            parts = [part.strip() for part in message.split(',')]
            print(f"🔍 [LocationMatcher] Comma-separated parts: {parts}")
            
            # 먼저 도시 검색 (더 구체적이므로 우선순위)
            for part in parts:
                if part.lower() not in non_location_words and len(part) > 2:  # 너무 짧은 단어는 제외
                    print(f"🔍 [LocationMatcher] Trying city search for part: '{part}'")
                    city_result = self.find_city(part)
                    if city_result["found"] and city_result["exact_match"]:
                        return {
                            "type": "city",
                            "result": city_result,
                            "original_text": part
                        }
            
            # 도시가 정확히 매칭되지 않으면 국가 검색
            for part in parts:
                if part.lower() not in non_location_words and len(part) > 2:  # 너무 짧은 단어는 제외
                    print(f"🔍 [LocationMatcher] Trying country search for part: '{part}'")
                    country_result = self.find_country(part)
                    if country_result["found"] and country_result["exact_match"]:
                        return {
                            "type": "country", 
                            "result": country_result,
                            "original_text": part
                        }
            
            # 정확한 매칭이 없으면 유사한 도시 제안
            for part in parts:
                if part.lower() not in non_location_words and len(part) > 2:  # 너무 짧은 단어는 제외
                    city_result = self.find_city(part)
                    if city_result["found"] and not city_result["exact_match"]:
                        return {
                            "type": "city",
                            "result": city_result,
                            "original_text": part
                        }
        
        # 단일 텍스트 처리 - 도시와 국가를 모두 시도하되, 더 유사한 것을 선택
        print(f"🔍 [LocationMatcher] Single text processing for: '{message}'")
        
        # 도시 검색
        city_result = self.find_city(message)
        print(f"🔍 [LocationMatcher] City result: {city_result}")
        
        # 국가 검색  
        country_result = self.find_country(message)
        print(f"🔍 [LocationMatcher] Country result: {country_result}")
        
        # 둘 다 찾았으면 더 정확한 것을 선택
        if city_result["found"] and country_result["found"]:
            # 정확한 매칭이 있는 것을 우선
            if city_result["exact_match"] and not country_result["exact_match"]:
                return {
                    "type": "city",
                    "result": city_result,
                    "original_text": message
                }
            elif country_result["exact_match"] and not city_result["exact_match"]:
                return {
                    "type": "country",
                    "result": country_result,
                    "original_text": message
                }
            else:
                # 둘 다 정확하거나 둘 다 유사한 경우, 유사도 점수 비교
                city_score = city_result.get("similarity_score", 0.5)
                country_score = country_result.get("similarity_score", 0.5)
                
                if city_score >= country_score:
                    return {
                        "type": "city",
                        "result": city_result,
                        "original_text": message
                    }
                else:
                    return {
                        "type": "country",
                        "result": country_result,
                        "original_text": message
                    }
        elif city_result["found"]:
            return {
                "type": "city",
                "result": city_result,
                "original_text": message
            }
        elif country_result["found"]:
            return {
                "type": "country",
                "result": country_result,
                "original_text": message
            }
        
        return {
            "type": "none",
            "result": {"found": False, "message": "위치 정보를 찾을 수 없습니다."},
            "original_text": message
        }

# 전역 인스턴스 생성
location_matcher = LocationMatcher()
