from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from climbing_conditions import fetch_hourly_weather_data, plot_hourly_climbing_scores, calculate_climbing_conditions_score
import logging

application = Flask(__name__)


# Secret key for session management
application.secret_key = 'tux'


@application.route('/')
def index():
    return render_template('index.html')


@application.route('/graph')
def graph():
    destination = request.args.get('destination', '')
    climbing_destinations = {
        "Yosemite National Park, USA": ("Yosemite Valley", "US"),
        "Joshua Tree National Park, USA": ("Joshua Tree", "US"),
        "Red River Gorge, USA": ("Slade", "US"),
        "Rocky Mountain National Park, USA": ("Estes Park", "US"),
        "Smith Rock State Park, USA": ("Terrebonne", "US"),
        "New River Gorge National Park, USA": ("Fayetteville", "US"),
    }

    if destination in climbing_destinations:
        city, country = climbing_destinations[destination]
        api_key = "59e23e27c5a507619213287828aca0bf"
        hourly_data = fetch_hourly_weather_data(api_key, city, country)
        if hourly_data:
            fig = plot_hourly_climbing_scores(hourly_data)
            return fig.to_json()  # Return graph data as JSON
        else:
            return "Failed to fetch weather data"
    else:
        return "Invalid destination"


# Add logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@application.route('/current_conditions')
def current_conditions():
    destination = request.args.get('destination', '')
    logger.info(f"Received request for current conditions for destination: {destination}")

    climbing_destinations = {
        "Yosemite National Park, USA": ("Yosemite Valley", "US"),
        "Joshua Tree National Park, USA": ("Joshua Tree", "US"),
        "Red River Gorge, USA": ("Slade", "US"),
        "Rocky Mountain National Park, USA": ("Estes Park", "US"),
        "Smith Rock State Park, USA": ("Terrebonne", "US"),
        "New River Gorge National Park, USA": ("Fayetteville", "US"),
    }

    if destination in climbing_destinations:
        city, country = climbing_destinations[destination]
        api_key = "59e23e27c5a507619213287828aca0bf"
        hourly_data = fetch_hourly_weather_data(api_key, city, country)
        if hourly_data:
            current_hour_data = hourly_data[0]  # Get data for the current hour
            logger.info(f"Received hourly data: {current_hour_data}")
            dew_point_f = current_hour_data['main']['feels_like']
            humidity = current_hour_data['main']['humidity']
            temp_f = current_hour_data['main']['temp']
            score = calculate_climbing_conditions_score(dew_point_f, humidity, temp_f)
            logger.info(f"Climbing conditions score calculated: {score}")

            # Round the climbing conditions score to one decimal place
            rounded_score = round(score, 1)

            # Construct JSON response with temperature, humidity, dew point, and rounded climbing conditions score
            response_data = {
                'temperature': temp_f,
                'humidity': humidity,
                'dew_point': dew_point_f,
                'climbing_conditions_score': rounded_score
            }

            return jsonify(response_data)
        else:
            logger.error("Failed to fetch weather data")
            return jsonify({'error': 'Failed to fetch weather data'}), 500
    else:
        logger.error("Invalid destination")
        return jsonify({'error': 'Invalid destination'}), 400


if __name__ == '__main__':
    application.run(debug=True)