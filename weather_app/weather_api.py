import time
import requests
from .utils import calculate_dew_point

def fetch_weather_data(api_key, lat, lon):
    def get_json(url, params):
        try:
            res = requests.get(url, params=params, timeout=10)
            return res.json() if res.status_code == 200 else None
        except requests.RequestException as e:
            print("Request error:", e)
            return None

    data_2_5 = get_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"}
    )
    data_3_0 = get_json(
        "https://api.openweathermap.org/data/3.0/onecall",
        {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial", "exclude": "minutely,alerts"}
    )

    if not data_2_5:
        print("[v2.5] Error fetching data.")
    if not data_3_0:
        print("[v3.0] Error fetching data.")

    return data_2_5, data_3_0

def fetch_hourly_weather_data(api_key, lat, lon):
    data_2_5, data_3_0 = fetch_weather_data(api_key, lat, lon)
    if not data_2_5 or not data_3_0:
        return None, None, None

    now = int(time.time())
    hourly_v3 = data_3_0.get("hourly", [])
    three_hour_v2 = data_2_5.get("list", [])
    daily_v3 = data_3_0.get("daily", [])

    current_v3 = data_3_0.get("current", {})
    current_weather = {
        'temp': current_v3.get('temp'),
        'humidity': current_v3.get('humidity'),
        'dew_point': current_v3.get('dew_point'),
        'wind_speed': current_v3.get('wind_speed'),
        'wind_gust': current_v3.get('wind_gust', 0),
        'wind_direction': current_v3.get('wind_gust', 0)
    }

    def adapt_entry(dt, temp, humidity, dew_point, wind, rain_accumulation, weather=None, pop=0):
        return {
            "dt": dt,
            "main": {
                "temp": temp,
                "humidity": humidity,
                "dew_point": dew_point
            },
            "weather": weather or [{"id": 800}],
            "pop": pop,
            "wind": wind,
            "rain_accumulation": rain_accumulation
        }

    adapted = []
    for entry in hourly_v3:
        if entry["dt"] >= now:
            adapted.append(adapt_entry(
                dt=entry["dt"],
                temp=entry["temp"],
                humidity=entry["humidity"],
                dew_point=entry["dew_point"],
                weather=entry.get("weather"),
                pop=entry.get("pop", 0),
                wind=entry.get("wind_speed", 0),
                rain_accumulation=entry.get("rain", {}).get("1h", 0)
            ))

    max_ts = max((e["dt"] for e in adapted), default=now)
    for entry in three_hour_v2:
        if entry["dt"] > max_ts:
            temp = entry["main"]["temp"]
            humidity = entry["main"]["humidity"]
            dew_point = calculate_dew_point(temp, humidity)
            wind_speed = entry.get("wind", {}).get("speed")
            rain_accumulation = entry.get("rain", {}).get("3h", 0)
            adapted.append(adapt_entry(
                dt=entry["dt"],
                temp=temp,
                humidity=humidity,
                dew_point=dew_point,
                weather=entry.get("weather"),
                pop=entry.get("pop", 0),
                wind=wind_speed,
                rain_accumulation=rain_accumulation
            ))

    max_ts = max((e["dt"] for e in adapted), default=max_ts)
    for entry in daily_v3:
        dt = entry["dt"] + 12 * 3600
        if dt > max_ts:
            adapted.append(adapt_entry(
                dt=dt,
                temp=entry["temp"]["day"],
                humidity=entry["humidity"],
                dew_point=entry["dew_point"],
                weather=entry.get("weather"),
                pop=entry.get("pop", 0),
                wind=entry.get("wind_speed", 0),
                rain_accumulation=entry.get("rain", 0)
            ))

    return current_weather, adapted, daily_v3
