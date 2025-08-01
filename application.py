from flask import Flask, render_template, request, jsonify
from climbing_conditions import (
    fetch_hourly_weather_data,
    plot_hourly_climbing_scores,
    plot_hourly_temp,
    plot_hourly_humidity,
    calculate_climbing_conditions_score,
    generate_daily_forecast
)
import os
import joblib
from datetime import datetime, timedelta

application = Flask(__name__)

# === Configuration ===
API_KEY = "59e23e27c5a507619213287828aca0bf"
MODEL_PATH = 'decision_tree_regression_model.pkl'

# Load trained model once at startup
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at '{MODEL_PATH}'")
model = joblib.load(MODEL_PATH)

# Available climbing destinations mapped to (city, country)
CLIMBING_DESTINATIONS = {
    "Black Canyon of the Gunnison, CO": ("Montrose", "US"),
    "Bishop, CA": ("Bishop", "US"),
    "Boone, NC": ("Boone", "US"),
    "Chattanooga, TN": ("Chattanooga", "US"),
    "Devils Tower National Monument, WY": ("Devils Tower National Monument", "US"),
    "Flagstaff, AZ": ("Flagstaff", "US"),
    "Hueco Tanks State Historic Site, TX": ("El Paso", "US"),
    "Indian Creek, UT": ("Moab", "US"),
    "Joshua Tree National Park, CA": ("Palm Springs", "US"),
    "Lander, WY": ("Lander", "US"),
    "Leavenworth, WA": ("Leavenworth", "US"),
    "Little Cottonwood Canyon, UT": ("Salt Lake City", "US"),
    "Looking Glass Rock, NC": ("Brevard", "US"),
    "Maple Canyon, UT": ("Moroni", "US"),
    "New River Gorge National Park, WV": ("Fayetteville", "US"),
    "Red River Gorge, KY": ("Slade", "US"),
    "Red Rock Canyon, NV": ("Las Vegas", "US"),
    "Rifle Mountain Park, CO": ("Rifle", "US"),
    "Rocky Mountain National Park, CO": ("Estes Park", "US"),
    "Rumney, NH": ("Plymouth", "US"),
    "Shawangunks, NY": ("Gardiner", "US"),
    "Smith Rock State Park, OR": ("Terrebonne", "US"),
    "Tacoma, WA": ("Tacoma", "US"),
    "The Needles, CA": ("Springville", "US"),
    "Yosemite National Park, CA": ("Yosemite National Park", "US"),
    "Zion National Park, UT": ("Zion National Park", "US")
}


@application.route('/')
def index():
    return render_template('index.html', areas=list(CLIMBING_DESTINATIONS.keys()))


@application.route('/all_data')
def all_data():
    destination = request.args.get('destination', '')
    tz_offset = int(request.args.get('tz_offset', default=0, type=int))  # in minutes
    tz_offset_sec = -tz_offset * 60  # 🟢 Subtract offset to shift to local time

    if destination not in CLIMBING_DESTINATIONS:
        return jsonify({'error': 'Invalid destination'}), 400

    city, country = CLIMBING_DESTINATIONS[destination]
    current_data, adapted, daily_v3 = fetch_hourly_weather_data(API_KEY, city, country)

    if not current_data or not adapted:
        return jsonify({'error': 'Failed to fetch weather data'}), 500

    # Shift current time
    if 'dt' in current_data:
        current_data['dt'] += tz_offset_sec

    # Shift adapted forecast entries
    for entry in adapted:
        if 'dt' in entry:
            entry['dt'] += tz_offset_sec

    # Shift daily forecast entries
    if daily_v3:
        for entry in daily_v3:
            if 'dt' in entry:
                entry['dt'] += tz_offset_sec

    temp = current_data['temp']
    humidity = current_data['humidity']
    dew_point = current_data['dew_point']
    score = round(calculate_climbing_conditions_score(model, dew_point, humidity, temp), 1)

    forecast = generate_daily_forecast(adapted, model)

    return jsonify({
        'conditions': {
            'climbing_conditions_score': score,
            'current': {
                'temp': temp,
                'humidity': humidity,
                'dew_point': dew_point
            },
            'forecast': forecast
        },
        'graphs': {
            'ccs': plot_hourly_climbing_scores(model, adapted, city, destination).to_json(),
            'temperature': plot_hourly_temp(model, adapted, city, destination).to_json(),
            'humidity': plot_hourly_humidity(model, adapted, city, destination).to_json()
        }
    })


if __name__ == '__main__':
    application.run()
