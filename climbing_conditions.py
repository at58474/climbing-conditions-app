"""Climbing Conditions controller

climbing_conditions.py contains the following functions:
    * fetch_hourly_weather_data(api_key, city, country) -
    * calculate_climbing_conditions_score(dew_point_f, humidity, temp_f) -
    * plot_hourly_climbing_scores(hourly_data, city_display, destination_display) -
"""

import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go


def fetch_hourly_weather_data(api_key, city, country):
    """Uses an API IRL Path to fetch weather data from openweathermap.com using api_key provided

    Parameters
    ----------
    api_key : str
        the API key to access weather data from openweathermmap.com
    city : str
        The first tuple value from the climbing_destinations dictionary value, city closest to destination
    country : str
        The second tuple value from the climbing_destinations dictionary value, country destination is in

    Returns
    -------
    hourly_data
        this is the collected hourly weather data which is used in the get_destination function, which is used in the
        functions graph() and current_conditions()
    """

    # Hourly API request by city name openweathermap.org url in the format:
    #   https://pro.openweathermap.org/data/2.5/forecast/hourly?q={city name},{country code}&appid={API key}
    #   API response is in JSON format which can be viewed here:
    #       https://openweathermap.org/api/hourly-forecast
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city},{country}&appid={api_key}&units=imperial"
    # part of the request library, returns a status code and request response object, accessible via response.json()
    response = requests.get(url)
    # status code 200 is OK, 404 is Not Found
    if response.status_code == 200:
        # uses json() method to fetch data from the API request.get() in dictionary format
        data = response.json()
        # This is the only way to check if hour is less than 24 that worked, is it really needed though?
        # hourly_data = [hour_data for hour_data in data['list'] if datetime.utcfromtimestamp(hour_data['dt']).hour < 24]
        hourly_data = [hour_data for hour_data in data['list']]
        # the list of weather data is stored into the hourly_data list and returned
        return hourly_data
    else:
        print("Failed to fetch weather data")
        return None


def calculate_climbing_conditions_score(model, dew_point, humidity, temperature):
    # Predicting the climbing conditions score for the given temperature and humidity
    score = model.predict([(temperature, humidity)])[0]

    # Check if temperature is equal to dew point and apply penalty if true
    if temperature == dew_point:
        if score - 2 < 0:
            return 0  # Set score to 0 if temperature equals dew point but the score will be less than 0
        else:
            return score - 2  # Subtract 2 points from the score if the rock is likely to be condenses
    return score


def get_weather_icon(weather_id):
    if 200 <= weather_id < 300:
        weather_icon = '⛈️'  # Thunderstorm
    elif 300 <= weather_id < 600:
        weather_icon = '🌧️'  # Rain
    elif 600 <= weather_id < 700:
        weather_icon = '🌨️'  # Snow
    elif 700 <= weather_id < 800:
        weather_icon = '🌫️'  # Mist/Fog/Smoke
    elif weather_id == 800:
        weather_icon = '☀️'  # Clear sky
    elif weather_id == 801:
        weather_icon = '🌤️'  # Few clouds
    elif 802 <= weather_id <= 804:
        weather_icon = '☁️'  # Cloudy
    else:
        weather_icon = '❓'  # Unknown weather condition

    return weather_icon


def plot_hourly_climbing_scores(model, hourly_data, city_display, destination_display):
    timestamps = []
    scores = []
    colors = []
    x_labels = []  # List to store x-axis labels with weather icons
    hover_text = []  # List to store hover text for each data point

    for hour_data in hourly_data:
        timestamp = datetime.utcfromtimestamp(hour_data['dt'])
        timestamps.append(timestamp)

        dew_point_f = hour_data['main']['feels_like']
        humidity = hour_data['main']['humidity']
        temp_f = hour_data['main']['temp']

        score = calculate_climbing_conditions_score(model, dew_point_f, humidity, temp_f)
        scores.append(score)

        if temp_f <= dew_point_f:
            colors.append('red')  # Set color to red if temp <= dew point
        else:
            colors.append('blue')  # Set color to blue otherwise

        # Determine weather condition and select appropriate Unicode character
        weather_id = hour_data['weather'][0]['id']
        weather_icon = get_weather_icon(weather_id)

        # Construct x-axis label with weather icon
        x_label = f"{weather_icon} {timestamp.strftime('%A')} {timestamp.strftime('%I:%M %p')}"
        x_labels.append(x_label)

        # Construct hover text
        hover_text.append(f"CCS: {score:.2f}<br>" +
                          f"Temperature: {temp_f:.2f}°F<br>" +
                          f"Humidity: {humidity}%<br>" +
                          f"Dew Point: {dew_point_f:.2f}°F")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=timestamps, y=scores, mode='lines+markers', marker=dict(color=colors),
                             hovertemplate="<b>%{x}</b><br>" +
                                           "%{text}<extra></extra>",
                             text=hover_text))

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

    fig.update_layout(title=f'CCS - {destination_display}',
                      xaxis=dict(title='Time', tickmode='array', tickvals=timestamps, ticktext=x_labels, tickangle=45),
                      yaxis=dict(title='CCS'),
                      showlegend=False)

    return fig


def plot_hourly_temp(model, hourly_data, city_display, destination_display):
    timestamps = []
    temps = []
    colors = []
    x_labels = []  # List to store x-axis labels with weather icons
    hover_text = []  # List to store hover text for each data point

    for hour_data in hourly_data:
        timestamp = datetime.utcfromtimestamp(hour_data['dt'])
        timestamps.append(timestamp)

        dew_point_f = hour_data['main']['feels_like']
        humidity = hour_data['main']['humidity']
        temp_f = hour_data['main']['temp']

        score = calculate_climbing_conditions_score(model, dew_point_f, humidity, temp_f)
        temps.append(temp_f)

        if temp_f <= dew_point_f:
            colors.append('red')  # Set color to red if temp <= dew point
        else:
            colors.append('blue')  # Set color to blue otherwise

        # Determine weather condition and select appropriate Unicode character
        weather_id = hour_data['weather'][0]['id']
        weather_icon = get_weather_icon(weather_id)

        # Construct x-axis label with weather icon
        x_label = f"{weather_icon} {timestamp.strftime('%A')} {timestamp.strftime('%I:%M %p')}"
        x_labels.append(x_label)

        # Construct hover text
        hover_text.append(f"CCS: {score:.2f}<br>" +
                          f"Temperature: {temp_f:.2f}°F<br>" +
                          f"Humidity: {humidity}%<br>" +
                          f"Dew Point: {dew_point_f:.2f}°F")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=timestamps, y=temps, mode='lines+markers', marker=dict(color=colors),
                             hovertemplate="<b>%{x}</b><br>" +
                                           "%{text}<extra></extra>",
                             text=hover_text))

    for hour_data in hourly_data:
        hour_time = datetime.utcfromtimestamp(hour_data['dt']).time()
        if hour_time.hour >= 20 or hour_time.hour < 7:
            start_time = datetime.utcfromtimestamp(hour_data['dt'])
            end_time = start_time + timedelta(hours=1)
            fig.add_shape(type="rect",
                          x0=start_time, y0=min(temps),
                          x1=end_time, y1=max(temps),
                          line=dict(color="grey", width=0),
                          fillcolor="grey", opacity=0.3)

    for i in range(len(temps) - 1):
        x0 = timestamps[i]
        x1 = timestamps[i + 1]
        y0 = temps[i]
        y1 = temps[i + 1]

        if y0 < 25:
            color = "rgba(255, 0, 0, 0.3)"  # Red shade
        elif y0 >= 25 and y0 <= 35:
            color = "rgba(255, 255, 0, 0.3)"  # Yellow shade
        elif y0 >= 36 and y0 <= 65:
            color = "rgba(0, 255, 0, 0.3)"  # Green shade
        elif y0 >= 66 and y0 <= 80:
            color = "rgba(255, 255, 0, 0.3)"  # Yellow shade
        elif y0 > 80:
            color = "rgba(255, 0, 0, 0.3)"  # Red shade

        fig.add_shape(type="rect",
                      x0=x0, y0=min(temps),
                      x1=x1, y1=max(temps),
                      line=dict(color="rgba(0, 0, 0, 0)", width=0),
                      fillcolor=color, opacity=0.3)

    fig.update_layout(title=f'Temperature - {destination_display}',
                      xaxis=dict(title='Time', tickmode='array', tickvals=timestamps, ticktext=x_labels, tickangle=45),
                      yaxis=dict(title='Temp (F)'),
                      showlegend=False)

    return fig

def plot_hourly_humidity(model, hourly_data, city_display, destination_display):
    timestamps = []
    humids = []
    colors = []
    x_labels = []  # List to store x-axis labels with weather icons
    hover_text = []  # List to store hover text for each data point

    for hour_data in hourly_data:
        timestamp = datetime.utcfromtimestamp(hour_data['dt'])
        timestamps.append(timestamp)

        dew_point_f = hour_data['main']['feels_like']
        humidity = hour_data['main']['humidity']
        temp_f = hour_data['main']['temp']

        score = calculate_climbing_conditions_score(model, dew_point_f, humidity, temp_f)
        humids.append(humidity)

        if temp_f <= dew_point_f:
            colors.append('red')  # Set color to red if temp <= dew point
        else:
            colors.append('blue')  # Set color to blue otherwise

        # Determine weather condition and select appropriate Unicode character
        weather_id = hour_data['weather'][0]['id']
        weather_icon = get_weather_icon(weather_id)

        # Construct x-axis label with weather icon
        x_label = f"{weather_icon} {timestamp.strftime('%A')} {timestamp.strftime('%I:%M %p')}"
        x_labels.append(x_label)

        # Construct hover text
        hover_text.append(f"CCS: {score:.2f}<br>" +
                          f"Temperature: {temp_f:.2f}°F<br>" +
                          f"Humidity: {humidity}%<br>" +
                          f"Dew Point: {dew_point_f:.2f}°F")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=timestamps, y=humids, mode='lines+markers', marker=dict(color=colors),
                             hovertemplate="<b>%{x}</b><br>" +
                                           "%{text}<extra></extra>",
                             text=hover_text))

    for hour_data in hourly_data:
        hour_time = datetime.utcfromtimestamp(hour_data['dt']).time()
        if hour_time.hour >= 20 or hour_time.hour < 7:
            start_time = datetime.utcfromtimestamp(hour_data['dt'])
            end_time = start_time + timedelta(hours=1)
            fig.add_shape(type="rect",
                          x0=start_time, y0=min(humids),
                          x1=end_time, y1=max(humids),
                          line=dict(color="grey", width=0),
                          fillcolor="grey", opacity=0.3)

    for i in range(len(humids) - 1):
        x0 = timestamps[i]
        x1 = timestamps[i + 1]
        y0 = humids[i]
        y1 = humids[i + 1]

        if y0 < 35:
            color = "rgba(0, 255, 0, 0.3)"  # Green shade
        elif y0 >= 35 and y0 <= 45:
            color = "rgba(255, 255, 0, 0.3)"  # Yellow shade
        elif y0 > 45:
            color = "rgba(255, 0, 0, 0.3)"  # Red shade

        fig.add_shape(type="rect",
                      x0=x0, y0=min(humids),
                      x1=x1, y1=max(humids),
                      line=dict(color="rgba(0, 0, 0, 0)", width=0),
                      fillcolor=color, opacity=0.3)

    fig.update_layout(title=f'Humidity - {destination_display}',
                      xaxis=dict(title='Time', tickmode='array', tickvals=timestamps, ticktext=x_labels, tickangle=45),
                      yaxis=dict(title='Humidity (%)'),
                      showlegend=False)

    return fig

from collections import defaultdict
def generate_daily_forecast(hourly_data, model):
    daily_summary = defaultdict(list)

    for entry in hourly_data:
        dt = datetime.utcfromtimestamp(entry['dt'])
        date_str = dt.strftime('%Y-%m-%d')  # Group by date only

        temp = entry['main']['temp']
        humidity = entry['main']['humidity']
        dew_point = entry['main']['feels_like']
        chance_of_precip = entry.get('pop', 0) * 100  # Convert to percentage

        ccs = calculate_climbing_conditions_score(model, dew_point, humidity, temp)

        daily_summary[date_str].append({
            'temp': temp,
            'humidity': humidity,
            'ccs': ccs,
            'precip': chance_of_precip
        })

    # Aggregate into daily high/low summaries
    daily_forecast = []
    for date, entries in daily_summary.items():
        temps = [e['temp'] for e in entries]
        hums = [e['humidity'] for e in entries]
        scores = [e['ccs'] for e in entries]
        precips = [e['precip'] for e in entries]

        daily_forecast.append({
            'date': date,
            'temp_high': max(temps),
            'temp_low': min(temps),
            'humidity_high': max(hums),
            'humidity_low': min(hums),
            'ccs_high': max(scores),
            'ccs_low': min(scores),
            'precip_high': max(precips),
            'precip_low': min(precips)
        })

    return daily_forecast
