import requests
import time
from datetime import datetime
from collections import defaultdict
import plotly.graph_objects as go

# === UTILITY FUNCTIONS ===

def calculate_dew_point(temp, rh):
    return temp - ((100 - rh) / 5.0)

def calculate_climbing_conditions_score(model, dew_point, humidity, temperature):
    score = model.predict([(temperature, humidity)])[0]
    return max(0, score - 2) if temperature == dew_point else score

def get_weather_icon(weather_id):
    if 200 <= weather_id < 300: return '⛈️'
    if 300 <= weather_id < 600: return '🌧️'
    if 600 <= weather_id < 700: return '🌨️'
    if 700 <= weather_id < 800: return '🌫️'
    if weather_id == 800: return '☀️'
    if weather_id == 801: return '🌤️'
    if 802 <= weather_id <= 804: return '☁️'
    return '❓'

# === WEATHER DATA FETCHING ===

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

    # === Step 1: Fetch weather data ===
    data_2_5, data_3_0 = fetch_weather_data(api_key, lat, lon)
    if not data_2_5 or not data_3_0:
        return None, None, None

    # === Step 3: Parse forecast data ===
    now = int(time.time())
    hourly_v3 = data_3_0.get("hourly", [])
    three_hour_v2 = data_2_5.get("list", [])
    daily_v3 = data_3_0.get("daily", [])

    # === Step 4: Parse current weather from v3.0 ===
    current_v3 = data_3_0.get("current", {})
    current_weather = {
        'temp': current_v3.get('temp'),
        'humidity': current_v3.get('humidity'),
        'dew_point': current_v3.get('dew_point'),  # now correctly sourced
        'wind_speed': current_v3.get('wind_speed'),
        'wind_gust': current_v3.get('wind_gust', 0),
        'wind_direction': current_v3.get('wind_gust', 0)
    }

    # === Step 5: Adapter helper ===
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

    # === Step 6: Adapt hourly (v3.0) ===
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

    # === Step 7: Adapt 3-hour (v2.5) ===
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
                rain_accumulation = rain_accumulation
            ))

    # === Step 8: Adapt daily (v3.0) ===
    max_ts = max((e["dt"] for e in adapted), default=max_ts)
    for entry in daily_v3:
        dt = entry["dt"] + 12 * 3600  # Midday timestamp
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


# === PLOTTING UTILITIES ===

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

def process_hourly_data(adapted, model, value_type):
    values, colors, x_labels, hover_text = [], [], [], []

    for entry in adapted:
        dt = datetime.utcfromtimestamp(entry['dt'])
        temp = entry['main']['temp']
        rh = entry['main']['humidity']
        dew_point = entry['main']['dew_point']
        score = calculate_climbing_conditions_score(model, dew_point, rh, temp)
        value = {'score': score, 'temp': temp, 'humidity': rh}[value_type]

        values.append(value)
        colors.append('red' if dew_point >= temp else 'blue')

        icon = get_weather_icon(entry['weather'][0]['id'])
        time_str = dt.strftime('%A %I:%M %p')
        rain = entry.get('pop', 0) * 100

        x_labels.append(f"{icon} {time_str}")
        hover_text.append(
            f"{icon} {time_str}<br>"
            f"CCS: {score:.2f}<br>Temp: {temp:.2f}°F<br>"
            f"Humidity: {rh}%<br>Dew Point: {dew_point:.2f}°F<br>"
            f"Chance of Rain: {rain:.0f}%"
        )

    x_indices = list(range(len(adapted)))
    return x_indices, values, colors, x_labels, hover_text

def plot_data(x_indices, values, colors, x_labels, hover_text, title, yaxis_title, color_ranges):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_indices,
        y=values,
        mode='lines+markers',
        marker=dict(color=colors),
        text=hover_text,
        hovertemplate="<b>%{text}</b><extra></extra>"
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

    # Add section dividers
    fig.add_vline(x=48, line_dash="dot", line_color="black", opacity=0.5)
    fig.add_vline(x=71, line_dash="dot", line_color="black", opacity=0.5)

    fig.add_annotation(x=24, y=1.10, yref="paper", text="Hourly", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=60, y=1.10, yref="paper", text="3-Hour", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=73, y=1.10, yref="paper", text="Daily", showarrow=False, font=dict(size=12))

    fig.update_layout(
        title=title,
        xaxis=dict(title='Time', tickmode='array', tickvals=x_indices, ticktext=x_labels, tickangle=45),
        yaxis=dict(title=yaxis_title),
        showlegend=False
    )

    return fig


# === PLOT WRAPPERS ===

def plot_hourly_climbing_scores(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'score')
    return plot_data(ts, vals, cols, labels, hover, f'CCS - {destination}', 'CCS', color_range_for_ccs)

def plot_hourly_temp(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'temp')
    return plot_data(ts, vals, cols, labels, hover, f'Temperature - {destination}', 'Temp (°F)', color_range_for_temp)

def plot_hourly_humidity(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'humidity')
    return plot_data(ts, vals, cols, labels, hover, f'Humidity - {destination}', 'Humidity (%)', color_range_for_humidity)

# === DAILY FORECAST ===

def generate_daily_forecast(adapted, model):
    grouped = defaultdict(list)
    for entry in adapted:
        date = datetime.utcfromtimestamp(entry['dt']).strftime('%Y-%m-%d')
        grouped[date].append(entry)

    forecast = []
    for idx, date in enumerate(sorted(grouped)[:8]):
        entries = grouped[date]
        temps = [e['main']['temp'] for e in entries]
        hums = [e['main']['humidity'] for e in entries]
        dew_points = [e['main']['dew_point'] for e in entries]
        pops = [e.get('pop', 0) * 100 for e in entries]
        winds = [e.get('wind', 0) for e in entries if e.get('wind') is not None]
        rains = [e.get('rain_accumulation', 0) for e in entries if e.get('rain_accumulation') is not None]

        ccs_values = [
            calculate_climbing_conditions_score(model, e['main']['dew_point'], e['main']['humidity'], e['main']['temp'])
            for e in entries
        ]

        forecast.append({
            'date': date,
            'source': 'hourly' if idx < 2 else '3-hour' if idx < 5 else 'daily',
            'temp_low': round(min(temps), 1),
            'temp_high': round(max(temps), 1),
            'humidity_low': round(min(hums)),
            'humidity_high': round(max(hums)),
            'ccs_low': round(min(ccs_values), 1),
            'ccs_high': round(max(ccs_values), 1),
            'precip_high': round(max(pops), 1),
            'wind_low': round(min(winds)) if winds else None,
            'wind_high': round(max(winds)) if winds else None,
            'rain_accumulation': round(sum(rains) / 25.4, 2) if rains else 0
        })

    return forecast
