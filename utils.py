import streamlit as st
import requests
from geopy.geocoders import Nominatim

# ---------- Geocoding ----------
@st.cache_data(ttl=86400)
def get_coordinates_from_place(place_name):
    try:
        geolocator = Nominatim(user_agent="gvan_forest")
        location = geolocator.geocode(place_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
        return None, None

# ---------- Climate & rainfall (Open-Meteo, free) ----------
@st.cache_data(ttl=86400)
def get_climate_and_rainfall(lat, lon):
    """Returns (annual_rainfall_mm, climate_zone_string)"""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "daily": ["precipitation_sum", "temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto"
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        daily = data['daily']
        # Rainfall
        precip = daily['precipitation_sum']
        annual_rainfall = sum([p for p in precip if p is not None])
        # Temperature based climate classification
        t_max = daily['temperature_2m_max']
        t_min = daily['temperature_2m_min']
        avg_temp = sum(t_max) / len(t_max)  # rough mean of max temps
        if avg_temp > 18:
            # Check aridity: low rainfall and high temp range
            if annual_rainfall < 500:
                climate = "Arid"
            else:
                climate = "Tropical"
        elif avg_temp > 0:
            climate = "Temperate"
        else:
            climate = "Cold"
        return annual_rainfall, climate
    except Exception as e:
        return None, "Temperate"  # fallback

# ---------- Soil type from SoilGrids (free) ----------
@st.cache_data(ttl=604800)
def get_soil_type(lat, lon):
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["clay", "sand", "silt"],
        "depth": "0-5cm",
        "value": "mean"
    }
    try:
        r = requests.get(url, params=params, headers={"Accept": "application/json"})
        data = r.json()
        sand = data['properties']['layers'][0]['depths'][0]['values']['mean'].get('sand', 0)
        clay = data['properties']['layers'][0]['depths'][0]['values']['mean'].get('clay', 0)
        if sand > 70:
            return "Sandy"
        elif clay > 40:
            return "Clay"
        else:
            return "Loamy"
    except:
        return "Loamy"

# ---------- NDVI estimate (rainfall-based) ----------
def get_ndvi_from_rainfall(rainfall_mm):
    if rainfall_mm > 1500:
        return 0.7
    elif rainfall_mm > 800:
        return 0.5
    elif rainfall_mm > 400:
        return 0.3
    else:
        return 0.15

# ---------- Polygon area calculation ----------
def calculate_polygon_area(coords):
    area = 0
    for i in range(len(coords)):
        x1, y1 = coords[i]
        x2, y2 = coords[(i+1) % len(coords)]
        area += (x1 * y2 - x2 * y1)
    return abs(area) / 2.0