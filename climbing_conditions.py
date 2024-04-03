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


def calculate_climbing_conditions_score(dew_point_f, humidity, temp_f):

    # This sets a weight value for dew point, humidity, and temperature based on an assumed importance. Experimentation
    # may be required to get these weights to be as accurate as possible. This is suggesting humidity and temperature
    # are both more important in determining climbing conditions than dew point, although dew point is still
    # significantly important.
    dew_point_weight = 2
    humidity_weight = 3
    temp_weight = 3

    # This sets high and low ranges for optimal climbing performance. These ranges can also be experimented with.
    # These ranges are used below to calculate a penalty to the ccs score, if outside the optimal range.
    optimal_dew_point_max = 40
    optimal_humidity_min = 25
    optimal_humidity_max = 35
    optimal_temp_min = 40
    optimal_temp_max = 69

    # If the dew point is outside of the optimal range, either high or low, a penalty is added as follows assuming
    #   dew_point max is set to 40:
    #   - If dew point were 45, then the dew point penalty would be (50-40) / 10 = 1
    #   - More examples:
    #        - (60-40) / 10 = 2
    #        - (85-40) / 10 = 4.6
    # If dew point is in range no penalty is added, also there is no dew point minimum since anthing under 40 is good
    #   and anything under can be penalized through the humidity and temperature ranges
    if dew_point_f > optimal_dew_point_max:
        dew_point_penalty = (dew_point_f - optimal_dew_point_max) / 10
    else:
        dew_point_penalty = 0

    # If the humidity is between the optimal_humidity_min and optimal_humidity_max values then no penalty is added,
    #   but if outside the range a penalty is added just like in the dew point penalty script above, but there is a
    #   min and max range
    if optimal_humidity_min <= humidity <= optimal_humidity_max:
        humidity_penalty = 0
    elif humidity < optimal_humidity_min:
        humidity_penalty = (optimal_humidity_min - humidity) / 10
    else:
        humidity_penalty = (humidity - optimal_humidity_max) / 10

    # If the temperature  is less than or equal to the dew point(even though it is impossible for the temperature to be
    #   less than dew point), then it is likely that the rock will be condensed and an additional penalty is added to
    #   the CCS score to reflect this suboptimal condition.
    if temp_f <= dew_point_f:
        temp_penalty = 2

    # Calculates temperature penalty if necessary
    elif optimal_temp_min <= temp_f <= optimal_temp_max:
        temp_penalty = 0
    elif temp_f < optimal_temp_min:
        temp_penalty = (optimal_temp_min - temp_f) / 10
    else:
        temp_penalty = (temp_f - optimal_temp_max) / 10

    # Since the CCS will be transformed to a scale from 0-10, this calculated the raw CCS score
    # Assuming the following:
    #   dew point = 50
    #   humidity = 60
    #   temperature = 70
    # The formula is (2 * (1-1)) +
    #                 3 * (1-2.5) +
    #                 3 * 0.1)
    #                = -4.8
    raw_ccs = (dew_point_weight * (1 - dew_point_penalty)) + \
              (humidity_weight * (1 - humidity_penalty)) - \
              (temp_weight * temp_penalty)

    # This transforms the rew score to be between 0 and 10
    min_score = -20
    max_score = 20
    # If the raw_css score were -4.8, then:
    #   (1 + (((-4.8-(-20)) / (20-(-20)) * 9)) =
    normalized_score = 1 + ((raw_ccs - min_score) / (max_score - min_score)) * 9

    return normalized_score


def plot_hourly_climbing_scores(hourly_data, city_display, destination_display):
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

        score = calculate_climbing_conditions_score(dew_point_f, humidity, temp_f)
        scores.append(score)

        if temp_f <= dew_point_f:
            colors.append('red')  # Set color to red if temp <= dew point
        else:
            colors.append('blue')  # Set color to blue otherwise

        # Determine weather condition and select appropriate Unicode character
        weather_id = hour_data['weather'][0]['id']
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

    fig.update_layout(title=f'Hourly Climbing Conditions Score for {city_display}, near {destination_display}',
                      xaxis=dict(title='Time', tickmode='array', tickvals=timestamps, ticktext=x_labels, tickangle=45),
                      yaxis=dict(title='Score'),
                      showlegend=False)

    return fig
