import requests
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.graph_objects as go
import time

# === Weather Data Fetching ===

def fetch_weather_data(api_key, lat, lon):
    url_2_5 = "https://api.openweathermap.org/data/2.5/forecast"
    params_2_5 = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "imperial"
    }

    url_3_0 = "https://api.openweathermap.org/data/3.0/onecall"
    params_3_0 = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "imperial",
        "exclude": "minutely,alerts"
    }

    try:
        response_2_5 = requests.get(url_2_5, params=params_2_5, timeout=10)
        response_3_0 = requests.get(url_3_0, params=params_3_0, timeout=10)

        data_2_5 = response_2_5.json() if response_2_5.status_code == 200 else None
        data_3_0 = response_3_0.json() if response_3_0.status_code == 200 else None

        if not data_2_5:
            print(f"[v2.5] Error {response_2_5.status_code}: {response_2_5.text}")
        if not data_3_0:
            print(f"[v3.0] Error {response_3_0.status_code}: {response_3_0.text}")

        return data_2_5, data_3_0

    except requests.exceptions.RequestException as e:
        print("Network error:", e)
        return None, None

def fetch_hourly_weather_data(api_key, city, country):
    # 1. Get coordinates from city/country
    geo_url = f"http://api.openweathermap.org/data/2.5/weather?q={city},{country}&appid={api_key}"
    geo_res = requests.get(geo_url)
    if geo_res.status_code != 200:
        print("Geocoding failed")
        return None, None, None

    loc_data = geo_res.json()
    lat, lon = loc_data['coord']['lat'], loc_data['coord']['lon']

    # 2. Fetch both 2.5 and 3.0 data
    data_2_5, data_3_0 = fetch_weather_data(api_key, lat, lon)
    if not data_2_5 or not data_3_0:
        return None, None, None

    # 3. Extract live current data from 2.5
    current_raw = data_2_5.get("current", {})
    if not current_raw or 'main' not in current_raw:
        # Fallback to first 2.5 hourly record
        first = data_2_5.get("list", [{}])[0]
        current_weather = {
            'temp': first.get('main', {}).get('temp'),
            'humidity': first.get('main', {}).get('humidity'),
            'dew_point': first.get('main', {}).get('feels_like')
        }
    else:
        current_weather = {
            'temp': current_raw['main']['temp'],
            'humidity': current_raw['main']['humidity'],
            'dew_point': current_raw['main']['feels_like']
        }

    # 4. Prepare forecast data
    now = int(time.time())
    hourly_v3 = data_3_0.get("hourly", [])
    three_hr_v2 = data_2_5.get("list", [])
    daily_v3 = data_3_0.get("daily", [])

    def calculate_dew_point(temp, rh):
        return temp - ((100 - rh) / 5.0)

    def adapt_v3_to_v2(entry):
        return {
            "dt": entry["dt"],
            "main": {
                "temp": entry["temp"],
                "humidity": entry["humidity"],
                "feels_like": entry["dew_point"]
            },
            "weather": entry.get("weather", [{"id": 800}]),
            "pop": entry.get("pop", 0)
        }

    def adapt_v2_5_entry(entry):
        temp = entry['main']['temp']
        rh = entry['main']['humidity']
        dew_point = calculate_dew_point(temp, rh)
        return {
            "dt": entry["dt"],
            "main": {
                "temp": temp,
                "humidity": rh,
                "feels_like": dew_point
            },
            "weather": entry.get("weather", [{"id": 800}]),
            "pop": entry.get("pop", 0)
        }

    def adapt_v3_daily_to_v2(entry):
        dt = entry["dt"] + 12 * 3600  # midday
        return {
            "dt": dt,
            "main": {
                "temp": entry["temp"]["day"],
                "humidity": entry["humidity"],
                "feels_like": entry["dew_point"]
            },
            "weather": entry.get("weather", [{"id": 800}]),
            "pop": entry.get("pop", 0)
        }

    # 5. Adapt entries from each source
    adapted = [adapt_v3_to_v2(h) for h in hourly_v3 if h["dt"] >= now]
    max_ts = max((entry["dt"] for entry in adapted), default=now)
    adapted += [adapt_v2_5_entry(e) for e in three_hr_v2 if e["dt"] > max_ts]
    max_ts = max((entry["dt"] for entry in adapted), default=max_ts)
    adapted += [adapt_v3_daily_to_v2(d) for d in daily_v3 if d["dt"] + 12 * 3600 > max_ts]

    return current_weather, adapted, daily_v3


# === Score Calculation ===

def calculate_climbing_conditions_score(model, dew_point, humidity, temperature):
    score = model.predict([(temperature, humidity)])[0]
    return max(0, score - 2) if temperature == dew_point else score

# === Weather Icons ===

def get_weather_icon(weather_id):
    if 200 <= weather_id < 300: return '⛈️'
    if 300 <= weather_id < 600: return '🌧️'
    if 600 <= weather_id < 700: return '🌨️'
    if 700 <= weather_id < 800: return '🌫️'
    if weather_id == 800: return '☀️'
    if weather_id == 801: return '🌤️'
    if 802 <= weather_id <= 804: return '☁️'
    return '❓'

# === Data Processing & Plotting Helpers ===

def process_hourly_data(hourly_data, model, value_type):
    values, colors, x_labels, hover_text = [], [], [], []

    for idx, hour in enumerate(hourly_data):
        timestamp = datetime.utcfromtimestamp(hour['dt'])
        temp = hour['main']['temp']
        humidity = hour['main']['humidity']
        dew_point = hour['main']['feels_like']
        weather_id = hour['weather'][0]['id']

        score = calculate_climbing_conditions_score(model, dew_point, humidity, temp)
        val = {'score': score, 'temp': temp, 'humidity': humidity}[value_type]
        values.append(val)

        marker_color = 'red' if dew_point >= temp else 'blue'
        colors.append(marker_color)

        icon = get_weather_icon(weather_id)
        time_str = timestamp.strftime('%A %I:%M %p')
        chance_of_rain = hour.get('pop', 0) * 100
        x_labels.append(f"{icon} {time_str}")
        hover_text.append(
            f"{icon} {time_str}<br>"
            f"CCS: {score:.2f}<br>"
            f"Temp: {temp:.2f}°F<br>"
            f"Humidity: {humidity}%<br>"
            f"Dew Point: {dew_point:.2f}°F<br>"
            f"Chance of Rain: {chance_of_rain:.0f}%"
        )

    x_indices = list(range(len(hourly_data)))

    return x_indices, values, colors, x_labels, hover_text


def plot_data(x_indices, values, colors, x_labels, hover_text, title, yaxis_title, color_ranges):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_indices,
        y=values,
        mode='lines+markers',
        marker=dict(color=colors),
        hovertemplate="<b>%{text}</b><extra></extra>",
        text=hover_text
    ))

    for i in range(len(values) - 1):
        fig.add_shape(
            type="rect",
            x0=i, x1=i + 1,
            y0=min(values), y1=max(values),
            line=dict(width=0),
            fillcolor=color_ranges(values[i]),
            opacity=0.3
        )

    fig.add_vline(x=48, line_dash="dot", line_color="black", opacity=0.5)
    fig.add_vline(x=64, line_dash="dot", line_color="black", opacity=0.5)
    fig.add_annotation(x=24, y=1.05, yref="paper", text="Hourly", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=56, y=1.05, yref="paper", text="3-Hour", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=72, y=1.05, yref="paper", text="Daily", showarrow=False, font=dict(size=12))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title='Time',
            tickmode='array',
            tickvals=x_indices,
            ticktext=x_labels,
            tickangle=45
        ),
        yaxis=dict(title=yaxis_title),
        showlegend=False
    )

    return fig

# === Color Mapping Functions ===

def color_range_for_temp(y):
    if y < 25: return "rgba(255, 0, 0, 0.3)"
    if y <= 35: return "rgba(255, 255, 0, 0.3)"
    if y <= 65: return "rgba(0, 255, 0, 0.3)"
    if y <= 80: return "rgba(255, 255, 0, 0.3)"
    return "rgba(255, 0, 0, 0.3)"

def color_range_for_humidity(y):
    if y < 35: return "rgba(0, 255, 0, 0.3)"
    if y <= 45: return "rgba(255, 255, 0, 0.3)"
    return "rgba(255, 0, 0, 0.3)"

def color_range_for_ccs(y):
    if y < 4: return "rgba(255, 0, 0, 0.3)"
    if y <= 6: return "rgba(255, 255, 0, 0.3)"
    return "rgba(0, 255, 0, 0.3)"

# === Plotting Functions ===

def plot_hourly_climbing_scores(model, hourly_data, city_display, destination_display):
    ts, vals, cols, labels, hover = process_hourly_data(hourly_data, model, 'score')
    return plot_data(ts, vals, cols, labels, hover, f'CCS - {destination_display}', 'CCS', color_range_for_ccs)

def plot_hourly_temp(model, hourly_data, city_display, destination_display):
    ts, vals, cols, labels, hover = process_hourly_data(hourly_data, model, 'temp')
    return plot_data(ts, vals, cols, labels, hover, f'Temperature - {destination_display}', 'Temp (°F)', color_range_for_temp)

def plot_hourly_humidity(model, hourly_data, city_display, destination_display):
    ts, vals, cols, labels, hover = process_hourly_data(hourly_data, model, 'humidity')
    return plot_data(ts, vals, cols, labels, hover, f'Humidity - {destination_display}', 'Humidity (%)', color_range_for_humidity)

# === Daily Forecast Summary ===

from collections import defaultdict
from datetime import datetime, timedelta

from collections import defaultdict
from datetime import datetime

def generate_daily_forecast(adapted, model):
    grouped = defaultdict(list)

    # Group entries by UTC date string
    for entry in adapted:
        date = datetime.utcfromtimestamp(entry['dt']).strftime('%Y-%m-%d')
        grouped[date].append(entry)

    sorted_dates = sorted(grouped.keys())[:8]  # Limit to 8 days
    forecast = []

    for idx, date in enumerate(sorted_dates):
        entries = grouped[date]

        # Determine the data type
        if idx < 2:
            source_type = "hourly"
        elif idx < 5:
            source_type = "3-hour"
        else:
            source_type = "daily"

        temps = [e['main']['temp'] for e in entries]
        hums = [e['main']['humidity'] for e in entries]
        dew_points = [e['main']['feels_like'] for e in entries]
        precips = [e.get('pop', 0) * 100 for e in entries]

        temp_min = min(temps)
        temp_max = max(temps)
        humidity_min = min(hums)
        humidity_max = max(hums)

        # ✅ Compute CCS per timestamp
        ccs_values = []
        for e in entries:
            temp = e['main']['temp']
            humidity = e['main']['humidity']
            dew_point = e['main']['feels_like']
            ccs = calculate_climbing_conditions_score(model, dew_point, humidity, temp)
            ccs_values.append(ccs)

        ccs_low = min(ccs_values) if ccs_values else 0
        ccs_high = max(ccs_values) if ccs_values else 0

        forecast.append({
            'date': date,
            'source': source_type,
            'temp_low': round(temp_min, 1),
            'temp_high': round(temp_max, 1),
            'humidity_low': round(humidity_min),
            'humidity_high': round(humidity_max),
            'ccs_low': round(ccs_low, 1),
            'ccs_high': round(ccs_high, 1),
            'precip_high': round(max(precips), 1)
        })

    return forecast




