import requests
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go

def fetch_hourly_weather_data(api_key, city, country):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city},{country}&appid={api_key}&units=imperial"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        hourly_data = [hour_data for hour_data in data['list'] if datetime.utcfromtimestamp(hour_data['dt']).hour < 24]
        return hourly_data
    else:
        print("Failed to fetch weather data")
        return None

def calculate_climbing_conditions_score(dew_point_f, humidity, temp_f):
    dew_point_weight = 2
    humidity_weight = 3
    temp_weight = 3

    optimal_dew_point_max = 40
    optimal_humidity_min = 25
    optimal_humidity_max = 35
    optimal_temp_min = 40
    optimal_temp_max = 69

    if dew_point_f > optimal_dew_point_max:
        dew_point_penalty = (dew_point_f - optimal_dew_point_max) / 10
    else:
        dew_point_penalty = 0

    if optimal_humidity_min <= humidity <= optimal_humidity_max:
        humidity_penalty = 0
    elif humidity < optimal_humidity_min:
        humidity_penalty = (optimal_humidity_min - humidity) / 10
    else:
        humidity_penalty = (humidity - optimal_humidity_max) / 10

    if temp_f <= dew_point_f:  # Adjusted condition for severe penalty, condensed rock
        temp_penalty = 2  # Severe penalty
    elif optimal_temp_min <= temp_f <= optimal_temp_max:
        temp_penalty = 0
    elif temp_f < optimal_temp_min:
        temp_penalty = (optimal_temp_min - temp_f) / 10
    else:
        temp_penalty = (temp_f - optimal_temp_max) / 10

    raw_ccs = (dew_point_weight * (1 - dew_point_penalty)) + \
              (humidity_weight * (1 - humidity_penalty)) - \
              (temp_weight * temp_penalty)

    min_score = -20
    max_score = 20
    normalized_score = 1 + ((raw_ccs - min_score) / (max_score - min_score)) * 9

    return normalized_score

def plot_hourly_climbing_scores(hourly_data):
    timestamps = []
    scores = []
    colors = []
    hover_texts = []

    for hour_data in hourly_data:
        timestamp = datetime.utcfromtimestamp(hour_data['dt'])
        timestamps.append(timestamp)

        dew_point_f = hour_data['main']['feels_like']
        humidity = hour_data['main']['humidity']
        temp_f = hour_data['main']['temp']

        score = calculate_climbing_conditions_score(dew_point_f, humidity, temp_f)
        scores.append(score)

        if temp_f <= dew_point_f:
            colors.append('red')  # Set color to red if temp <= dew point
        else:
            colors.append('blue')  # Set color to blue otherwise

        # Create hover text
        hover_text = f"Temperature: {temp_f}°F<br>Humidity: {humidity}%<br>Dew Point: {dew_point_f}°F"
        hover_texts.append(hover_text)

    x_labels = [f"{ts.strftime('%A')} {ts.strftime('%I:%M %p')}" for ts in timestamps]

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=timestamps, y=scores, mode='lines+markers', marker=dict(color=colors),
                             hovertext=hover_texts, hoverinfo="text"))

    for hour_data in hourly_data:
        hour_time = datetime.utcfromtimestamp(hour_data['dt']).time()
        if hour_time.hour >= 20 or hour_time.hour < 7:
            start_time = datetime.utcfromtimestamp(hour_data['dt'])
            end_time = start_time + timedelta(hours=1)
            fig.add_shape(type="rect",
                          x0=start_time, y0=min(scores),
                          x1=end_time, y1=max(scores),
                          line=dict(color="grey", width=0),
                          fillcolor="grey", opacity=0.3)

    # Add background shading based on climbing conditions score ranges
    for i in range(len(scores) - 1):
        x0 = timestamps[i]
        x1 = timestamps[i + 1]
        y0 = scores[i]
        y1 = scores[i + 1]

        if y0 < 4:
            color = "rgba(255, 0, 0, 0.3)"  # Red shade
        elif y0 >= 4 and y0 <= 6:
            color = "rgba(255, 255, 0, 0.3)"  # Yellow shade
        else:
            color = "rgba(0, 255, 0, 0.3)"  # Green shade

        fig.add_shape(type="rect",
                      x0=x0, y0=min(scores),
                      x1=x1, y1=max(scores),
                      line=dict(color="rgba(0, 0, 0, 0)", width=0),
                      fillcolor=color, opacity=0.3)

    fig.update_layout(title='Hourly Climbing Conditions Score',
                      xaxis=dict(title='Time', tickmode='array', tickvals=timestamps, ticktext=x_labels, tickangle=45),
                      yaxis=dict(title='Score'),
                      showlegend=False)

    return fig