from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form
import ee
import pandas as pd
import requests
import os
from pathlib import Path
from typing import List, Optional
import json
import tempfile
from dotenv import load_dotenv


router = APIRouter()
load_dotenv()

# --- GEE Setup ---
def gee_initialize():
    """Initialize Google Earth Engine with service account authentication."""
    try:
        service_account_file = os.getenv('GOOGLE_CREDENTIALS')  # JSON 파일 경로 또는 JSON 문자열
        if not service_account_file:
            raise ValueError("GOOGLE_CREDENTIALS env variable not found.")
        
        # JSON 파일 경로인지 JSON 문자열인지 확인
        if service_account_file.startswith('{'):
            # JSON 문자열인 경우 임시 파일로 저장
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
                json.dump(json.loads(service_account_file), f)
                temp_path = f.name
        else:
            # 파일 경로인 경우
            temp_path = service_account_file
        
        if os.path.exists(temp_path):
            credentials = ee.ServiceAccountCredentials(
                email='gee-demo@dataground-demo.iam.gserviceaccount.com',  # JSON의 client_email 사용
                key_file=temp_path,
            )
            ee.Initialize(credentials, project='dataground-demo')
            print("GEE initialized with service account authentication")
        else:
            print(f"Service account file '{service_account_file}' not found. Attempting interactive authentication...")
            ee.Authenticate()
            ee.Initialize(project='dataground-demo')
            print("GEE initialized with interactive authentication")
            
    except Exception as e:
        print(f"Error initializing GEE: {str(e)}")
        try:
            ee.Authenticate()
            ee.Initialize(project='dataground-demo')
            print("GEE initialized with interactive authentication (fallback)")
        except Exception as e2:
            print(f"Failed to initialize GEE: {str(e2)}")
            raise

# === OLD CODE (ahj personal account)===
# def gee_initialize():
#     """Initialize Google Earth Engine with the specified project."""
#     try:
#         ee.Initialize(project='data-ground-demo')
#     except Exception:
#         ee.Authenticate()
#         ee.Initialize(project='data-ground-demo')

gee_initialize()

# Use Jakarta bounding box polygon
jakarta_geom = ee.Geometry.BBox(106.689, -6.365, 106.971, -6.089)
jakarta_area_km2 = jakarta_geom.area(10).divide(1e6).getInfo()

@router.get("/sea-level-rise")
def slr_risk(
    min_lat: float = Query(-6.365, description="Minimum latitude of bounding box (default: Jakarta)"),
    min_lon: float = Query(106.689, description="Minimum longitude of bounding box (default: Jakarta)"),
    max_lat: float = Query(-6.089, description="Maximum latitude of bounding box (default: Jakarta)"),
    max_lon: float = Query(106.971, description="Maximum longitude of bounding box (default: Jakarta)"),
    threshold: float = Query(2.0, description="Elevation threshold in meters (default: 2.0, range: 0.0-5.0)")
):
    """
    Returns a PNG URL for the SLR risk mask (areas below the threshold) for the specified bounding box.
    The risk region is colored red, and ocean areas are excluded using a land mask.
    The threshold parameter (in meters) is passed from the frontend and can be set in the range 0.0-5.0.
    """
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    srtm = ee.Image("USGS/SRTMGL1_003").clip(bbox)
    # Land mask: Use 2020 image from MODIS Land Cover Type 1, 0 = water
    modis_landcover = ee.ImageCollection('MODIS/006/MCD12Q1') \
        .filter(ee.Filter.calendarRange(2020, 2020, 'year')) \
        .first()
    land_mask = modis_landcover.select('LC_Type1').clip(bbox).neq(0)
    # SLR risk on land only
    slr_mask = srtm.lt(threshold).And(land_mask)
    url = slr_mask.getThumbURL({
        'min': 0,
        'max': 1,
        'palette': ['white', 'red'],
        'dimensions': 512,
        'region': bbox
    })
    
    # Calculate risk area statistics
    # Calculate number of risk pixels to estimate area
    risk_pixels = slr_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=bbox,
        scale=30,  # SRTM resolution
        maxPixels=1e9
    ).getInfo()
    
    total_pixels = bbox.area(10).getInfo() / (30 * 30)  # Number of pixels based on 30m resolution
    risk_area = risk_pixels.get('constant', 0) * 30 * 30  # Square meters
    total_area = bbox.area(10).getInfo()  # Square meters
    risk_percentage = (risk_area / total_area) * 100 if total_area > 0 else 0
    
    # Calculate center point
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    return {
        "url": url,
        "map_data": {
            "image_url": url,
            "center": [center_lon, center_lat],
            "zoom": 10,
            "bbox": [min_lon, min_lat, max_lon, max_lat]
        },
        "chart_data": {
            "risk_area_km2": risk_area / 1e6,  # Convert to square kilometers
            "total_area_km2": total_area / 1e6,
            "risk_percentage": round(risk_percentage, 2),
            "threshold": threshold
        },
        "analysis_type": "sea_level_rise",
        "parameters": {
            "threshold": threshold,
            "bbox": [min_lon, min_lat, max_lon, max_lat]
        }
    }

@router.get("/urban-area-map")
def urban_area_map(
    year: int = Query(2020, description="Year (>=2001, <=2020)"),
    min_lat: float = Query(-6.365),
    min_lon: float = Query(106.689),
    max_lat: float = Query(-6.089),
    max_lon: float = Query(106.971)
):
    if not (2001 <= year <= 2020):
        raise HTTPException(status_code=400, detail="Year must be between 2001 and 2020.")
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    img = ee.ImageCollection('MODIS/006/MCD12Q1').filter(ee.Filter.calendarRange(year, year, 'year')).first()
    urban = img.select('LC_Type1').eq(13)
    url = urban.getThumbURL({
        'min': 0, 'max': 1, 'palette': ['white', 'red'],
        'dimensions': 512, 'region': bbox
    })
    return {"url": url}

@router.get("/urban-area-stats")
def urban_area_stats(
    year: int = Query(2020, description="Year (>=2001, <=2020)"),
    threshold: float = Query(2.0, description="Elevation threshold in meters (default: 2.0, range: 0.0-5.0)")
):
    if not (2001 <= year <= 2020):
        raise HTTPException(status_code=400, detail="Year must be between 2001 and 2020.")
    
    img = ee.ImageCollection('MODIS/006/MCD12Q1').filter(ee.Filter.calendarRange(year, year, 'year')).first()
    urban = img.select('LC_Type1').eq(13)
    
    # Total urban area (km^2)
    pixel_area_total = urban.multiply(ee.Image.pixelArea()).clip(jakarta_geom)
    area_m2_total = pixel_area_total.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=jakarta_geom,
        scale=500,
        maxPixels=1e9
    ).get('LC_Type1')
    area_km2_total = ee.Number(area_m2_total).divide(1e6)
    
    # Urban area in risk (km^2)
    srtm = ee.Image("USGS/SRTMGL1_003").clip(jakarta_geom)
    slr_mask = srtm.lt(threshold)
    urban_in_risk = urban.And(slr_mask)
    pixel_area = urban_in_risk.multiply(ee.Image.pixelArea()).clip(jakarta_geom)
    area_m2 = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=jakarta_geom,
        scale=500,
        maxPixels=1e9
    ).get('LC_Type1')
    area_km2 = ee.Number(area_m2).divide(1e6)
    
    # Population in urban area
    try:
        pop_img = ee.Image(f'WorldPop/GP/100m/pop/IDN_{year}').clip(jakarta_geom)
        pop_in_urban_val = pop_img.updateMask(urban).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=jakarta_geom,
            scale=100,
            maxPixels=1e9
        ).get('population')
    except Exception:
        pop_in_urban_val = 0
    
    # Population in urban & risk area
    try:
        pop_in_urban_risk_val = pop_img.updateMask(urban_in_risk).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=jakarta_geom,
            scale=100,
            maxPixels=1e9
        ).get('population')
    except Exception:
        pop_in_urban_risk_val = 0
    
    # Evaluate
    total_urban_area = area_km2_total.getInfo()
    urban_area_in_risk = area_km2.getInfo()
    pop_in_urban = pop_in_urban_val.getInfo() if pop_in_urban_val else 0
    pop_in_urban_risk = pop_in_urban_risk_val.getInfo() if pop_in_urban_risk_val else 0
    
    # Urbanization percentage
    urbanization_pct = (total_urban_area / jakarta_area_km2) * 100 if jakarta_area_km2 > 0 else 0
    
    return {
        "year": year,
        "total_urban_area": total_urban_area,
        "urban_area_in_risk": urban_area_in_risk,
        "pop_in_urban": pop_in_urban,
        "pop_in_urban_risk": pop_in_urban_risk,
        "urbanization_pct": urbanization_pct,
        "jakarta_area_km2": jakarta_area_km2
    }

@router.get("/population-exposure-map")
def population_exposure_map(
    year: int = Query(2020, description="Year (2000-2020 for WorldPop)"),
    threshold: float = Query(2.0, description="SLR threshold in meters") ,
    min_lat: float = Query(-6.365),
    min_lon: float = Query(106.689),
    max_lat: float = Query(-6.089),
    max_lon: float = Query(106.971)
):
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    # Use WorldPop for population (2000-2020)
    if not (2000 <= year <= 2020):
        year = 2020
    pop_img = ee.Image(f'WorldPop/GP/100m/pop/IDN_{year}').clip(bbox)
    pop_density = pop_img
    # Classify density
    low = pop_density.lt(100)
    medium = pop_density.gte(100).And(pop_density.lt(1000))
    high = pop_density.gte(1000)
    srtm = ee.Image("USGS/SRTMGL1_003").clip(bbox)
    slr_mask = srtm.lt(threshold)
    high_risk = high.And(slr_mask)
    class_img = low.multiply(0).add(medium.multiply(1)).add(high.multiply(2)).add(high_risk.multiply(3))
    palette = ['#ffffb2', '#fecc5c', '#fd8d3c', '#b10026']
    url = class_img.visualize(min=0, max=3, palette=palette).getThumbURL({
        'dimensions': 512,
        'region': bbox
    })
    return {"url": url}

@router.get("/population-exposure-trend")
def population_exposure_trend(
    start_year: int = Query(2015, description="Start year (2000-2020)"),
    end_year: int = Query(2020, description="End year (2000-2020)"),
    threshold: float = Query(2.0, description="SLR threshold in meters"),
    min_lat: float = Query(-6.365),
    min_lon: float = Query(106.689),
    max_lat: float = Query(-6.089),
    max_lon: float = Query(106.971)
):
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    years = [y for y in range(start_year, end_year + 1) if 2000 <= y <= 2020]
    total_pop = []
    high_risk_pop = []
    for year in years:
        pop_img = ee.Image(f'WorldPop/GP/100m/pop/IDN_{year}').clip(bbox)
        pop_density = pop_img
        srtm = ee.Image("USGS/SRTMGL1_003").clip(bbox)
        slr_mask = srtm.lt(threshold)
        total = pop_density.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bbox,
            scale=100,
            maxPixels=1e9
        ).get('population')
        high_risk = pop_density.updateMask(slr_mask).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=bbox,
            scale=100,
            maxPixels=1e9
        ).get('population')
        total_pop.append(total)
        high_risk_pop.append(high_risk)
    total_pop_vals = ee.List(total_pop).getInfo()
    high_risk_vals = ee.List(high_risk_pop).getInfo()
    return {"years": years, "total_population": total_pop_vals, "high_risk_population": high_risk_vals}

@router.get("/urban-area-comprehensive-stats")
def urban_area_comprehensive_stats(
    start_year: int = Query(2014, description="Start year (>=2001, <=2020)"),
    end_year: int = Query(2020, description="End year (>=2001, <=2020, >=start_year)"),
    threshold: float = Query(2.0, description="Elevation threshold in meters (default: 2.0, range: 0.0-5.0)")
):
    if not (2001 <= start_year <= 2020 and 2001 <= end_year <= 2020 and start_year <= end_year):
        raise HTTPException(status_code=400, detail="Years must be between 2001 and 2020 and start_year <= end_year.")
    
    years = list(range(start_year, end_year + 1))
    urban_areas = []
    urban_areas_in_risk = []
    populations_in_urban = []
    populations_in_urban_risk = []
    total_populations = []
    
    for year in years:
        img = ee.ImageCollection('MODIS/006/MCD12Q1').filter(ee.Filter.calendarRange(year, year, 'year')).first()
        urban = img.select('LC_Type1').eq(13)
        
        # Total urban area (km^2)
        pixel_area_total = urban.multiply(ee.Image.pixelArea()).clip(jakarta_geom)
        area_m2_total = pixel_area_total.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=jakarta_geom,
            scale=500,
            maxPixels=1e9
        ).get('LC_Type1')
        area_km2_total = ee.Number(area_m2_total).divide(1e6)
        urban_areas.append(area_km2_total)
        
        # Urban area in risk (km^2)
        srtm = ee.Image("USGS/SRTMGL1_003").clip(jakarta_geom)
        slr_mask = srtm.lt(threshold)
        urban_in_risk = urban.And(slr_mask)
        pixel_area = urban_in_risk.multiply(ee.Image.pixelArea()).clip(jakarta_geom)
        area_m2 = pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=jakarta_geom,
            scale=500,
            maxPixels=1e9
        ).get('LC_Type1')
        area_km2 = ee.Number(area_m2).divide(1e6)
        urban_areas_in_risk.append(area_km2)
        
        # Population data
        try:
            pop_img = ee.Image(f'WorldPop/GP/100m/pop/IDN_{year}').clip(jakarta_geom)
            
            # Total population in study area
            total_pop = pop_img.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=jakarta_geom,
                scale=100,
                maxPixels=1e9
            ).get('population')
            total_populations.append(total_pop)
            
            # Population in urban area
            pop_in_urban_val = pop_img.updateMask(urban).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=jakarta_geom,
                scale=100,
                maxPixels=1e9
            ).get('population')
            populations_in_urban.append(pop_in_urban_val)
            
            # Population in urban & risk area
            pop_in_urban_risk_val = pop_img.updateMask(urban_in_risk).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=jakarta_geom,
                scale=100,
                maxPixels=1e9
            ).get('population')
            populations_in_urban_risk.append(pop_in_urban_risk_val)
            
        except Exception:
            total_populations.append(0)
            populations_in_urban.append(0)
            populations_in_urban_risk.append(0)
    
    # Evaluate all values
    urban_areas_vals = ee.List(urban_areas).getInfo()
    urban_areas_in_risk_vals = ee.List(urban_areas_in_risk).getInfo()
    populations_in_urban_vals = ee.List(populations_in_urban).getInfo()
    populations_in_urban_risk_vals = ee.List(populations_in_urban_risk).getInfo()
    total_populations_vals = ee.List(total_populations).getInfo()
    
    # Calculate summary statistics
    start_urban_area = urban_areas_vals[0] if urban_areas_vals else 0
    end_urban_area = urban_areas_vals[-1] if urban_areas_vals else 0
    end_urban_area_in_risk = urban_areas_in_risk_vals[-1] if urban_areas_in_risk_vals else 0
    end_pop_in_urban = populations_in_urban_vals[-1] if populations_in_urban_vals else 0
    end_pop_in_urban_risk = populations_in_urban_risk_vals[-1] if populations_in_urban_risk_vals else 0
    end_total_pop = total_populations_vals[-1] if total_populations_vals else 0
    
    # Urbanization percentage (end year)
    urbanization_pct = (end_urban_area / jakarta_area_km2) * 100 if jakarta_area_km2 > 0 else 0
    
    # Urbanization change ratio (start to end year)
    urbanization_change_ratio = 0
    if start_urban_area > 0:
        urbanization_change_ratio = ((end_urban_area - start_urban_area) / start_urban_area) * 100
    
    # Population ratios
    pop_ratio_urban = (end_pop_in_urban / end_total_pop) * 100 if end_total_pop > 0 else 0
    pop_ratio_urban_risk = (end_pop_in_urban_risk / end_total_pop) * 100 if end_total_pop > 0 else 0
    
    return {
        "start_year": start_year,
        "end_year": end_year,
        "years": years,
        "urban_areas": urban_areas_vals,
        "urban_areas_in_risk": urban_areas_in_risk_vals,
        "populations_in_urban": populations_in_urban_vals,
        "populations_in_urban_risk": populations_in_urban_risk_vals,
        "total_populations": total_populations_vals,
        "summary": {
            "start_year": start_year,
            "end_year": end_year,
            "urban_area_end_year": end_urban_area,
            "urban_area_in_risk_end_year": end_urban_area_in_risk,
            "urbanization_pct": urbanization_pct,
            "urbanization_change_ratio": urbanization_change_ratio,
            "population_in_urban": end_pop_in_urban,
            "population_in_urban_risk": end_pop_in_urban_risk,
            "population_ratio_urban": pop_ratio_urban,
            "population_ratio_urban_risk": pop_ratio_urban_risk,
            "jakarta_area_km2": jakarta_area_km2
        }
    }

@router.get("/urban-area-risk-combined-map")
def urban_area_risk_combined_map(
    year: int = Query(2020, description="Year (>=2001, <=2020)"),
    threshold: float = Query(2.0, description="Elevation threshold in meters (default: 2.0, range: 0.0-5.0)"),
    min_lat: float = Query(-6.365),
    min_lon: float = Query(106.689),
    max_lat: float = Query(-6.089),
    max_lon: float = Query(106.971)
):
    """
    Returns a combined map showing urban areas and sea level risk areas.
    Urban areas are shown in pink, and urban areas at risk are shown in red.
    """
    if not (2001 <= year <= 2020):
        raise HTTPException(status_code=400, detail="Year must be between 2001 and 2020.")
    
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    
    # Get urban area
    img = ee.ImageCollection('MODIS/006/MCD12Q1').filter(ee.Filter.calendarRange(year, year, 'year')).first()
    urban = img.select('LC_Type1').eq(13)
    
    # Get sea level risk mask
    srtm = ee.Image("USGS/SRTMGL1_003").clip(bbox)
    modis_landcover = ee.ImageCollection('MODIS/006/MCD12Q1') \
        .filter(ee.Filter.calendarRange(2020, 2020, 'year')) \
        .first()
    land_mask = modis_landcover.select('LC_Type1').clip(bbox).neq(0)
    slr_mask = srtm.lt(threshold).And(land_mask)
    
    # Combine urban and risk areas
    # 0 = non-urban, 1 = urban, 2 = urban at risk
    urban_at_risk = urban.And(slr_mask)
    urban_not_at_risk = urban.And(slr_mask.Not())
    
    # Create classification image
    classification = urban_not_at_risk.multiply(1).add(urban_at_risk.multiply(2))
    
    url = classification.getThumbURL({
        'min': 0,
        'max': 2,
        'palette': ['white', 'pink', 'red'],
        'dimensions': 512,
        'region': bbox
    })
    return {"url": url}

@router.get("/infrastructure-exposure")
def infrastructure_exposure(
    year: int = Query(2020, description="Year (>=2001, <=2020)"),
    threshold: float = Query(2.0, description="Elevation threshold in meters (default: 2.0, range: 0.0-5.0)"),
    min_lat: float = Query(-6.365),
    min_lon: float = Query(106.689),
    max_lat: float = Query(-6.089),
    max_lon: float = Query(106.971)
):
    """
    Returns infrastructure exposure analysis with map and infrastructure data.
    Shows critical infrastructure (hospitals, schools, police, fire stations, government) at risk from sea level rise.
    """
    if not (2001 <= year <= 2020):
        raise HTTPException(status_code=400, detail="Year must be between 2001 and 2020.")
    
    bbox = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    
    # Try to fetch real infrastructure data from OSM Overpass API
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f'''
    [out:json][timeout:25];
    (
      node["amenity"="hospital"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["amenity"="school"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["amenity"="police"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["amenity"="fire_station"]({min_lat},{min_lon},{max_lat},{max_lon});
      node["office"="government"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body;
    '''
    infra_data = []
    try:
        resp = requests.post(overpass_url, data={'data': overpass_query}, timeout=30)
        if resp.status_code == 200:
            osm = resp.json()
            for el in osm.get('elements', []):
                name = el.get('tags', {}).get('name', 'Unknown')
                if 'amenity' in el.get('tags', {}):
                    t = el['tags']['amenity']
                elif 'office' in el.get('tags', {}):
                    t = el['tags']['office']
                else:
                    t = 'other'
                # Normalize type
                if t == 'fire_station': t = 'Fire Station'
                elif t == 'police': t = 'Police Station'
                elif t == 'hospital': t = 'Hospital'
                elif t == 'school': t = 'School'
                elif t == 'government': t = 'Government Agency'
                else: t = t.title()
                infra_data.append({
                    'name': name,
                    'type': t,
                    'lat': el['lat'],
                    'lon': el['lon']
                })
    except Exception as e:
        # Fallback to static data if OSM fails
        infra_data = [
            {"name": "RSUD Pasar Minggu", "type": "Hospital", "lat": -6.2921, "lon": 106.8234},
            {"name": "RS Fatmawati", "type": "Hospital", "lat": -6.2956, "lon": 106.7956},
            {"name": "RS Cipto Mangunkusumo", "type": "Hospital", "lat": -6.1754, "lon": 106.8272},
            {"name": "RS Jakarta Medical Center", "type": "Hospital", "lat": -6.1854, "lon": 106.8372},
            {"name": "RS Medistra", "type": "Hospital", "lat": -6.1954, "lon": 106.8472},
            {"name": "RS Siloam", "type": "Hospital", "lat": -6.2054, "lon": 106.8572},
            {"name": "SMA Negeri 1 Jakarta", "type": "School", "lat": -6.1754, "lon": 106.8272},
            {"name": "SMP Negeri 1 Jakarta", "type": "School", "lat": -6.1854, "lon": 106.8372},
            {"name": "SD Negeri 1 Jakarta", "type": "School", "lat": -6.1954, "lon": 106.8472},
            {"name": "SMA Negeri 2 Jakarta", "type": "School", "lat": -6.2054, "lon": 106.8572},
            {"name": "SMP Negeri 2 Jakarta", "type": "School", "lat": -6.2154, "lon": 106.8672},
            {"name": "SD Negeri 2 Jakarta", "type": "School", "lat": -6.2254, "lon": 106.8772},
            {"name": "Universitas Indonesia", "type": "School", "lat": -6.2354, "lon": 106.8872},
            {"name": "Institut Teknologi Bandung Jakarta", "type": "School", "lat": -6.2454, "lon": 106.8972},
            {"name": "Kantor Polisi Jakarta Pusat", "type": "Police Station", "lat": -6.1754, "lon": 106.8272},
            {"name": "Kantor Polisi Jakarta Selatan", "type": "Police Station", "lat": -6.2956, "lon": 106.7956},
            {"name": "Kantor Polisi Jakarta Utara", "type": "Police Station", "lat": -6.1154, "lon": 106.8772},
            {"name": "Kantor Polisi Jakarta Barat", "type": "Police Station", "lat": -6.1554, "lon": 106.7572},
            {"name": "Kantor Polisi Jakarta Timur", "type": "Police Station", "lat": -6.2354, "lon": 106.8872},
            {"name": "Pemadam Kebakaran Jakarta Pusat", "type": "Fire Station", "lat": -6.1754, "lon": 106.8272},
            {"name": "Pemadam Kebakaran Jakarta Selatan", "type": "Fire Station", "lat": -6.2956, "lon": 106.7956},
            {"name": "Pemadam Kebakaran Jakarta Utara", "type": "Fire Station", "lat": -6.1154, "lon": 106.8772},
            {"name": "Pemadam Kebakaran Jakarta Barat", "type": "Fire Station", "lat": -6.1554, "lon": 106.7572},
            {"name": "Pemadam Kebakaran Jakarta Timur", "type": "Fire Station", "lat": -6.2354, "lon": 106.8872},
            {"name": "Kantor Gubernur DKI Jakarta", "type": "Government Agency", "lat": -6.1754, "lon": 106.8272},
            {"name": "Kantor Walikota Jakarta Selatan", "type": "Government Agency", "lat": -6.2956, "lon": 106.7956},
            {"name": "Kantor Bupati Jakarta Utara", "type": "Government Agency", "lat": -6.1154, "lon": 106.8772},
            {"name": "Kantor Camat Jakarta Barat", "type": "Government Agency", "lat": -6.1554, "lon": 106.7572},
            {"name": "Kantor Lurah Jakarta Timur", "type": "Government Agency", "lat": -6.2354, "lon": 106.8872},
            {"name": "Dinas Pendidikan DKI Jakarta", "type": "Government Agency", "lat": -6.2454, "lon": 106.8972},
            {"name": "Dinas Kesehatan DKI Jakarta", "type": "Government Agency", "lat": -6.2554, "lon": 106.9072},
            {"name": "Dinas Lingkungan Hidup DKI Jakarta", "type": "Government Agency", "lat": -6.2654, "lon": 106.9172},
        ]
    df = pd.DataFrame(infra_data)
    
    # Batch elevation queries using GEE sampleRegions
    srtm = ee.Image("USGS/SRTMGL1_003")
    features = [ee.Feature(ee.Geometry.Point(row['lon'], row['lat']), {'idx': i}) for i, row in df.iterrows()]
    points_fc = ee.FeatureCollection(features)
    elevations_fc = srtm.sampleRegions(collection=points_fc, scale=30, geometries=True)
    elevations = elevations_fc.getInfo()
    idx_to_elev = {f['properties']['idx']: f['properties']['elevation'] for f in elevations['features']}
    df['elevation'] = df.index.map(idx_to_elev.get)
    df['at_risk'] = df['elevation'] < threshold
    
    # Filter infrastructure within the bounding box
    filtered_df = df[(df['lat'] >= min_lat) & (df['lat'] <= max_lat) & (df['lon'] >= min_lon) & (df['lon'] <= max_lon)]
    filtered_infrastructure = filtered_df.to_dict('records')
    
    # Generate map URL with risk areas in red
    slr_mask = srtm.lt(threshold)
    url = slr_mask.getThumbURL({
        'min': 0,
        'max': 1,
        'palette': ['white', 'red'],
        'dimensions': 512,
        'region': bbox
    })
    
    # Calculate statistics using pandas
    total_infrastructure = len(filtered_df)
    at_risk_infrastructure = len(filtered_df[filtered_df['at_risk'] == True])
    risk_percentage = (at_risk_infrastructure / total_infrastructure * 100) if total_infrastructure > 0 else 0
    
    # Group by type using pandas
    infrastructure_by_type = {}
    for infra_type in filtered_df['type'].unique():
        type_df = filtered_df[filtered_df['type'] == infra_type]
        infrastructure_by_type[infra_type] = {
            "total": len(type_df),
            "at_risk": len(type_df[type_df['at_risk'] == True])
        }
    
    return {
        "map_url": url,
        "infrastructure_data": filtered_infrastructure,
        "infrastructure_dataframe": filtered_df.to_dict('records'),
        "statistics": {
            "total_infrastructure": total_infrastructure,
            "at_risk_infrastructure": at_risk_infrastructure,
            "risk_percentage": risk_percentage,
            "by_type": infrastructure_by_type
        },
        "parameters": {
            "year": year,
            "threshold": threshold,
            "bbox": [min_lat, min_lon, max_lat, max_lon]
        }
    } 

@router.post("/topic-modeling")
async def topic_modeling(
    method: str = Form("lda"),
    n_topics: str = Form(""),  # Change to string to avoid validation issues
    min_df: float = Form(2.0),
    max_df: float = Form(0.95),
    ngram_range: str = Form("1,1"),
    text_input: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
):
    """
    Perform topic modeling on uploaded files or text input.
    """
    print("DEBUG: Topic modeling endpoint called")
    
    try:
        # Convert n_topics from string to int if provided
        n_topics_int = None
        if n_topics and n_topics.strip():
            try:
                n_topics_int = int(n_topics.strip())
            except ValueError:
                n_topics_int = None
        
        # Check if files are provided and their details
        if files:
            print(f"DEBUG: Number of files: {len(files)}")
            for i, file in enumerate(files):
                print(f"DEBUG: File {i+1}: {file.filename}, size: {file.size if hasattr(file, 'size') else 'unknown'} bytes")
        else:
            print("DEBUG: No files provided")
        
        # Method-specific parameter validation
        if method.lower() == "lda" and n_topics_int is None:
            raise HTTPException(
                status_code=400, 
                detail="n_topics parameter is required for LDA method. Please specify the number of topics."
            )
        elif method.lower() == "bertopic" and n_topics_int is not None and n_topics_int < 1:
            raise HTTPException(
                status_code=400, 
                detail="BERTopic n_topics must be >= 1 if specified, or leave empty for auto-detection."
            )
        
        # Import topic modeling (lazy import to avoid startup issues)
        from .topic_models import TopicModeling
        
        # Parse ngram range
        try:
            ngram_start, ngram_end = map(int, ngram_range.split(','))
            ngram_range_tuple = (ngram_start, ngram_end)
        except Exception as e:
            print(f"DEBUG: Error parsing ngram_range '{ngram_range}': {e}")
            raise HTTPException(status_code=400, detail=f"Invalid ngram_range format: {ngram_range}. Expected format: 'start,end'")
        
        # Convert min_df to appropriate type for scikit-learn
        # min_df can be int (>=1) or float (0.0-1.0)
        if min_df >= 1.0:
            min_df_final = int(min_df)
        else:
            min_df_final = float(min_df)
        
        
        # Prepare documents
        docs = []
        doc_names = []
        
        if text_input and text_input.strip():
            # Use text input
            docs.append(text_input.strip())
            doc_names.append("User Input Text")
            print(f"DEBUG: Added text input, length: {len(text_input.strip())}")
        
        if files:
            # Process uploaded files
            for file in files:
                if file.filename:
                    # Save file temporarily
                    file_path = Path("uploaded_files") / file.filename
                    file_path.parent.mkdir(exist_ok=True)
                    
                    with open(file_path, "wb") as buffer:
                        content = file.file.read()
                        buffer.write(content)
                    
                    # Read file content based on extension
                    if file_path.suffix.lower() == '.csv':
                        df = pd.read_csv(file_path)
                        # Assume first text column
                        text_col = None
                        for col in df.columns:
                            if df[col].dtype == 'object' and len(df[col].astype(str).str.len().mean()) > 10:
                                text_col = col
                                break
                        if text_col:
                            docs.extend(df[col].astype(str).tolist())
                            doc_names.extend([f"{file.filename}_{i}" for i in range(len(df))])
                    elif file_path.suffix.lower() in ['.txt', '.docx', '.pdf']:
                        # Use the topic_models file readers
                        from .topic_models import READERS
                        reader = READERS.get(file_path.suffix.lower())
                        if reader:
                            try:
                                content = reader(file_path)
                                if len(content.strip()) == 0:
                                    print(f"WARNING: No content extracted from {file.filename}")
                                docs.append(content)
                                doc_names.append(file.filename)
                            except Exception as e:
                                print(f"Error reading {file.filename}: {e}")
                    
                    # Clean up temporary file
                    file_path.unlink()
        
        
        if not docs:
            raise HTTPException(status_code=400, detail="No documents or text provided")
        
        # Check if all documents are empty after extraction
        non_empty_docs = [doc for doc in docs if doc.strip()]
        if len(non_empty_docs) == 0:
            raise HTTPException(status_code=400, detail="No text content could be extracted from the uploaded files. The files might be image-based or corrupted.")
        
        
        # Check if BERTopic is selected with insufficient documents
        if method.lower() == "bertopic" and len(docs) < 2:
            raise HTTPException(
                status_code=400, 
                detail=f"BERTopic requires at least 2 documents for meaningful topic modeling. You have {len(docs)} document(s). Please upload multiple files."
            )
        
        # Adjust parameters for document count scenarios
        if len(docs) == 1:
            print(f"DEBUG: Single document detected, adjusting parameters")
            if min_df_final > 1:
                min_df_final = 1
                print(f"DEBUG: Adjusted min_df to 1 for single document")
            if max_df < 1.0:
                max_df_final = 1.0
                print(f"DEBUG: Adjusted max_df to 1.0 for single document")
            else:
                max_df_final = max_df
        else:
            max_df_final = max_df
            # For multiple documents, ensure min_df doesn't exceed max_df constraint
            max_df_docs = int(len(docs) * max_df)
            if min_df_final > max_df_docs:
                min_df_final = max(1, max_df_docs)
                print(f"DEBUG: Adjusted min_df to {min_df_final} to satisfy max_df constraint")
            
            # For BERTopic, ensure we have sufficient data for meaningful clustering
            if method.lower() == "bertopic":
                # BERTopic needs more relaxed parameters for small document sets
                if len(docs) <= 5:
                    min_df_final = 1
                    max_df_final = 1.0
                elif len(docs) <= 10:
                    min_df_final = max(1, min_df_final)
                    max_df_final = min(1.0, max_df_final)
            
        # Initialize topic modeling
        
        # Prepare parameters for TopicModeling
        if method.lower() == "lda":
            # LDA requires all parameters
            tm_params = {
                'method': method.lower(),
                'n_topics': n_topics_int,
                'ngram_range': ngram_range_tuple,
                'min_df': min_df_final,
                'max_df': max_df_final,
                'random_state': 42
            }
        else:  # bertopic
            # BERTopic uses minimal parameters (auto-detects number of topics)
            tm_params = {
                'method': method.lower()
            }
            # BERTopic automatically determines number of topics
        
        # Create TopicModeling instance
        tm = TopicModeling(**tm_params)
        
        # Fit the model
        results = tm.fit(docs)
        
        # Get results
        topics = results['topics']
        document_topics = results['document_assignments']
        
        # Check if any topics were found
        if len(topics) == 0:
            print("DEBUG: No topics found by BERTopic. This can happen with small datasets or very diverse documents.")
            return {
                "topics": [],
                "document_topics": [],
                "wordclouds": [],
                "message": "No topics could be identified. This might be due to the documents being too diverse or the dataset being too small. Try using LDA method or uploading more similar documents."
            }
        
        # Generate wordclouds for all topics
        wordclouds = []
        
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            import io
            import base64
            
            for i, topic in enumerate(topics):
                # Prepare frequency data for wordcloud
                if method.lower() == "lda":
                    # For LDA, use the topic words and weights
                    freqs = {word: weight for word, weight in zip(topic['words'], topic['weights'])}
                else:  # bertopic
                    # For BERTopic, use the topic words and weights
                    freqs = {word: weight for word, weight in zip(topic['words'], topic['weights'])}
                
                # Create wordcloud
                wc = WordCloud(
                    width=800, 
                    height=400, 
                    background_color="white",
                    max_words=100,
                    colormap='viridis'
                ).generate_from_frequencies(freqs)
                
                # Convert to base64 image
                plt.figure(figsize=(10, 5))
                plt.imshow(wc, interpolation="bilinear")
                plt.axis("off")
                plt.title(f"Topic {i + 1} Wordcloud")
                
                # Save to bytes buffer
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
                img_buffer.seek(0)
                plt.close()
                
                # Convert to base64
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                wordclouds.append({
                    "topic_id": i + 1,  # 1-based indexing for users
                    "wordcloud_data": f"data:image/png;base64,{img_base64}",
                    "frequencies": freqs
                })
                
        except Exception as e:
            print(f"DEBUG: Wordcloud generation failed: {str(e)}")
            # Continue without wordclouds if they fail
            wordclouds = []
        
        # Prepare visualization data
        topic_data = []
        for i, topic in enumerate(topics):
            words = topic['words']
            weights = topic['weights']
            topic_data.append({
                "topic_id": i + 1,  # 1-based indexing for users
                "words": words,
                "weights": weights,
                "top_words": words[:10],  # Top 10 words for display
                "top_weights": weights[:10]
            })
        
        # Document-topic distribution
        doc_topic_data = []
        for i, doc_topic in enumerate(document_topics):
            doc_topic_data.append({
                "doc_id": i,
                "doc_name": doc_names[i] if i < len(doc_names) else f"doc_{i}",
                "dominant_topic": doc_topic['dominant_topic'] + 1,  # 1-based indexing
                "topic_probability": doc_topic['topic_probability'],
                "document_preview": doc_topic['document']
            })
        
        # Get model information
        model_info = results['model_info']
        
        print(f"DEBUG: Returning results with {len(topic_data)} topics and {len(wordclouds)} wordclouds")
        return {
            "method": method,
            "n_topics": model_info.get("n_topics", len(topic_data)),
            "is_auto_topic_detection": model_info.get("is_auto_topic_detection", method.lower() == "bertopic"),
            "topics": topic_data,
            "document_topics": doc_topic_data,
            "total_documents": len(docs),
            "document_names": doc_names,
            "wordclouds": wordclouds,
            "model_info": model_info
        }
        
    except Exception as e:
        print(f"DEBUG: Error in topic_modeling: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Topic modeling failed: {str(e)}")

@router.get("/topic-modeling-plot/{topic_id}")
async def get_topic_plot(
    topic_id: int,
    plot_type: str = Query("barchart"),  # "barchart", "wordcloud", "doc_topic"
    doc_index: Optional[int] = Query(None),
    topn: int = Query(15)
):
    """
    Generate topic modeling visualization plots.
    Note: This is a placeholder - in a real implementation, you'd generate and return image files.
    """
    return {
        "message": f"Plot generation for topic {topic_id}, type: {plot_type}",
        "topic_id": topic_id,
        "plot_type": plot_type,
        "doc_index": doc_index,
        "topn": topn
    }

@router.get("/topic-modeling-wordcloud/{topic_id}")
async def get_topic_wordcloud(
    topic_id: int,
    method: str = Query("lda"),
    n_topics: str = Query(""),  # Change to string to avoid validation issues
    min_df: float = Query(2.0),
    max_df: float = Query(0.95),
    ngram_range: str = Query("1,1"),
    text_input: Optional[str] = Query(None),
    max_words: int = Query(100)
):
    """
    Generate wordcloud for a specific topic.
    Note: This endpoint works best with text_input. For file-based analysis, 
    the wordcloud is generated from the main topic modeling results.
    """
    try:
        # Convert n_topics from string to int if provided
        n_topics_int = None
        if n_topics and n_topics.strip():
            try:
                n_topics_int = int(n_topics.strip())
            except ValueError:
                n_topics_int = None
        
        # Method-specific parameter validation
        if method.lower() == "lda" and n_topics_int is None:
            raise HTTPException(
                status_code=400, 
                detail="n_topics parameter is required for LDA method. Please specify the number of topics."
            )
        elif method.lower() == "bertopic" and n_topics_int is not None and n_topics_int < 1:
            raise HTTPException(
                status_code=400, 
                detail="BERTopic n_topics must be >= 1 if specified, or leave empty for auto-detection."
            )
        
        # For now, this endpoint only works with text input
        # File-based wordclouds should be generated from the main topic modeling results
        if not text_input or not text_input.strip():
            raise HTTPException(
                status_code=400, 
                detail="Wordcloud endpoint requires text_input. For file-based analysis, use the main topic modeling endpoint."
            )
        
        # Import topic modeling
        from .topic_models import TopicModeling
        
        # Parse ngram range
        ngram_start, ngram_end = map(int, ngram_range.split(','))
        ngram_range_tuple = (ngram_start, ngram_end)
        
        # Prepare documents
        docs = [text_input.strip()]
        doc_names = ["User Input Text"]
        
        # Adjust parameters for single document
        if min_df >= 1.0:
            min_df_final = int(min_df)
        else:
            min_df_final = float(min_df)
        max_df_final = 1.0
        
        # Prepare parameters for TopicModeling
        if method.lower() == "lda":
            # LDA requires all parameters
            tm_params = {
                'method': method.lower(),
                'n_topics': n_topics_int,
                'ngram_range': ngram_range_tuple,
                'min_df': min_df_final,
                'max_df': max_df_final,
                'random_state': 42
            }
        else:  # bertopic
            # BERTopic uses minimal parameters (auto-detects number of topics)
            tm_params = {
                'method': method.lower()
            }
            # BERTopic automatically determines number of topics
        
        # Initialize and fit model
        tm = TopicModeling(**tm_params)
        
        # Fit the model
        if method.lower() == "lda":
            tm.set_docs(docs, doc_names).preprocess().fit(n_iter=20)
        else:  # bertopic
            tm.set_docs(docs, doc_names).preprocess().fit()
        
        # Convert 1-based topic_id to 0-based for internal processing
        internal_topic_id = topic_id - 1
        if internal_topic_id < 0:
            raise HTTPException(status_code=400, detail="Topic ID must be >= 1")
        
        # Generate wordcloud for the specified topic
        if method.lower() == "lda":
            # For LDA, get topic components from the model
            comp = tm.model.lda.components_[internal_topic_id]
            vocab = tm.model.vocab
            freqs = {vocab[i]: float(comp[i]) for i in range(len(vocab))}
        else:  # bertopic
            # For BERTopic, get topic words
            topic = tm.model.model.get_topics().get(internal_topic_id)
            if topic is None:
                raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
            freqs = {w: float(wt) for w, wt in topic[:max_words]}
        
        # Generate wordcloud
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import io
        import base64
        
        # Create wordcloud
        wc = WordCloud(
            width=800, 
            height=400, 
            background_color="white",
            max_words=max_words,
            colormap='viridis'
        ).generate_from_frequencies(freqs)
        
        # Convert to base64 image
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.title(f"Topic {topic_id} Wordcloud")
        
        # Save to bytes buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
        img_buffer.seek(0)
        plt.close()
        
        # Convert to base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return {
            "topic_id": topic_id,
            "method": method,
            "wordcloud_data": f"data:image/png;base64,{img_base64}",
            "frequencies": freqs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wordcloud generation failed: {str(e)}") 