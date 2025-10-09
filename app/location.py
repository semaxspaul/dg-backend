from fastapi import APIRouter, HTTPException
import pandas as pd
import os
from typing import List, Dict

router = APIRouter()

# Path to the worldcities.csv file
WORLDCITIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "worldcities.csv")

@router.get("/countries", response_model=List[str])
def get_countries():
    """Get list of all unique countries from worldcities.csv"""
    try:
        # Read the CSV file
        df = pd.read_csv(WORLDCITIES_PATH)
        
        # Get unique countries and sort them
        countries = sorted(df['country'].unique().tolist())
        
        return countries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading worldcities data: {str(e)}")

@router.get("/cities/{country}", response_model=List[Dict[str, str]])
def get_cities_by_country(country: str):
    """Get list of cities for a specific country"""
    try:
        # Read the CSV file
        df = pd.read_csv(WORLDCITIES_PATH)
        
        # Filter by country
        country_data = df[df['country'] == country]
        
        # Get unique cities with their ascii names
        cities = country_data[['city', 'city_ascii']].drop_duplicates()
        
        # Convert to list of dictionaries
        cities_list = []
        for _, row in cities.iterrows():
            cities_list.append({
                "city": row['city'],
                "city_ascii": row['city_ascii']
            })
        
        # Sort by city name
        cities_list.sort(key=lambda x: x['city'])
        
        return cities_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading cities for {country}: {str(e)}")

@router.get("/cities", response_model=List[Dict[str, str]])
def get_all_cities():
    """Get all cities with their countries"""
    try:
        # Read the CSV file
        df = pd.read_csv(WORLDCITIES_PATH)
        
        # Get unique cities with their countries
        cities = df[['city', 'city_ascii', 'country']].drop_duplicates()
        
        # Convert to list of dictionaries
        cities_list = []
        for _, row in cities.iterrows():
            cities_list.append({
                "city": row['city'],
                "city_ascii": row['city_ascii'],
                "country": row['country']
            })
        
        # Sort by country then city name
        cities_list.sort(key=lambda x: (x['country'], x['city']))
        
        return cities_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading all cities: {str(e)}")

@router.get("/city-coordinates/{city_ascii}")
def get_city_coordinates(city_ascii: str):
    """Get coordinates (lat, lng) for a specific city by city_ascii"""
    try:
        # Read the CSV file
        df = pd.read_csv(WORLDCITIES_PATH)
        
        # Find the city by city_ascii
        city_data = df[df['city_ascii'] == city_ascii]
        
        if city_data.empty:
            raise HTTPException(status_code=404, detail=f"City '{city_ascii}' not found")
        
        # Get the first match (in case there are duplicates)
        city = city_data.iloc[0]
        
        return {
            "lat": float(city['lat']),
            "lng": float(city['lng']),
            "city": city['city'],
            "city_ascii": city['city_ascii'],
            "country": city['country']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting coordinates for {city_ascii}: {str(e)}")
