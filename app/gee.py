from fastapi import APIRouter, Query, HTTPException
import ee
import os
import json 
import tempfile

router = APIRouter()

def gee_initialize():
    """Initialize Google Earth Engine with service account authentication."""
    try:
        service_account_file = os.getenv('GOOGLE_CREDENTIALS')  #"dataground-demo-8e3edabd762a.json"
        if not service_account_file:
            raise ValueError("GOOGLE_CREDENTIALS env variable not found.")
        
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump(json.loads(service_account_file), f)
            temp_path = f.name
        
        if os.path.exists(temp_path):
            credentials = ee.ServiceAccountCredentials(
                email='dataground2025@gmail.com',
                key_file=temp_path,
            )
            ee.Initialize(credentials, project='dataground-469809')
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
            ee.Initialize(project='dataground-469809')
            print("GEE initialized with interactive authentication (fallback)")
        except Exception as e2:
            print(f"Failed to initialize GEE: {str(e2)}")
            raise

gee_initialize()

# Use Jakarta bounding box polygon
jakarta_geom = ee.Geometry.BBox(106.689, -6.365, 106.971, -6.089)
jakarta_area_km2 = jakarta_geom.area(10).divide(1e6).getInfo()

@router.get("/slr-risk")
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
    return {"url": url}

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