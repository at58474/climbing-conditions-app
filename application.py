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
    "Bishop, CA": (35.3023, -120.6944),
    "Black Canyon of the Gunnison, CO": (38.5791, -107.7276),
    "Boone, NC": (36.2164, -81.6747),
    "Broughton Bluff, OR": (45.5311, -122.3782),
    "Castle Rock State Park, CA": (37.2324, -122.1535),
    "Chattanooga, TN": (35.0456, -85.3097),
    "City of Rocks SP, NM": (32.5900, -107.9758),
    "City of Rocks, ID": (42.0699, -113.7124),
    "Clear Creek Canyon, CO": (39.7402, -105.2488),
    "Cochise Stronghold, AZ": (31.9022, -109.9770),
    "Currahee Mountain, GA": (34.5620, -83.3726),
    "Devil's Lake, WI": (43.4194, -89.7372),
    "Devils Tower National Monument, WY": (44.5902, -104.7146),
    "Eldorado Canyon, CO": (39.9313, -105.2832),
    "Enchanted Rock State Park, NM": (32.5900, -107.9758),
    "Enchanted Rock, TX": (30.5032, -98.8190),
    "Flagstaff, AZ": (35.1983, -111.6513),
    "Foster Falls, TN": (35.1756, -85.6401),
    "Frenchman Coulee (Vantage), WA": (47.02735, -120.00089),
    "Grand Ledge, MI": (42.7548, -84.7466),
    "Horse Pens 40, AL": (33.9320, -86.3239),
    "Hueco Tanks State Historic Site, TX": (31.9790, -106.0350),
    "Indian Creek, UT": (38.0371, -109.5481),
    "Index Town Walls, WA": (47.8222, -121.5548),
    "Joshua Tree National Park, CA": (33.8819, -115.9007),
    "Laurel Knob, NC": (35.1372, -82.9617),
    "Lander, WY": (42.8330, -108.7281),
    "Leavenworth, WA": (47.5965, -120.6610),
    "Linville Gorge, NC": (35.8903, -81.8976),
    "Little Cottonwood Canyon, UT": (40.6041, -111.6540),
    "Looking Glass Rock, NC": (35.2300, -82.8438),
    "Lost Wall, GA": (34.5958, -85.3585),
    "Lover's Leap, CA": (38.8234, -120.1414),
    "Maple Canyon, UT": (39.6539, -111.8631),
    "Mt. Erie, WA": (48.4206, -122.6435),
    "Mt. Lemmon, AZ": (32.4425, -110.7882),
    "New River Gorge National Park, WV": (37.9645, -81.0901),
    "Obed Wild & Scenic River, TN": (36.0968, -84.6890),
    "Red River Gorge, KY": (37.8339, -83.6078),
    "Red Rock Canyon, NV": (36.1566, -115.4451),
    "Red Wing, MN": (44.5667, -92.5333),
    "Rifle Mountain Park, CO": (39.5368, -107.7879),
    "Rocky Mountain National Park, CO": (40.3428, -105.6836),
    "Rumbling Bald, NC": (35.4552, -82.2345),
    "Rumney, NH": (43.9850, -71.7164),
    "Sandia Mountains, NM": (35.2090, -106.4442),
    "Shawangunks, NY": (41.7090, -74.1319),
    "Shelf Road, CO": (38.6183, -105.1962),
    "Smith Rock State Park, OR": (44.3263, -121.1319),
    "Spearfish Canyon, SD": (44.3697, -103.9064),
    "Stone Fort (Little Rock City), TN": (35.2026, -85.2369),
    "Tacoma, WA": (47.2529, -122.4443),
    "Tahquitz Rock / Suicide Rock, CA": (33.7602, -116.6832),
    "Ten Sleep Canyon, WY": (44.0951, -107.4026),
    "The Needles, CA": (36.9964, -118.6000),
    "Unaweep Canyon, CO": (38.7850, -108.6970),
    "Vedauwoo, WY": (41.1522, -105.3757),
    "Wichita Mountains, OK": (34.7233, -98.6119),
    "Wild Iris, WY": (42.6631, -108.7403),
    "Winslow Wall, AZ": (34.7397, -111.1345),
    "Yosemite National Park, CA": (37.8393, -119.5165),
    "Zion National Park, UT": (37.2978, -113.0288)
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

    lat, lon = CLIMBING_DESTINATIONS[destination]
    current_data, adapted, daily_v3 = fetch_hourly_weather_data(API_KEY, lat, lon)

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
    wind_speed = current_data['wind_speed']
    wind_gust = current_data['wind_gust']
    wind_direction = current_data['wind_direction']
    score = round(calculate_climbing_conditions_score(model, dew_point, humidity, temp), 1)

    forecast = generate_daily_forecast(adapted, model)

    return jsonify({
        'conditions': {
            'climbing_conditions_score': score,
            'current': {
                'temp': temp,
                'humidity': humidity,
                'dew_point': dew_point,
                'wind_speed': wind_speed,
                'wind_gust': wind_gust,
                'wind_direction': wind_direction
            },
            'forecast': forecast
        },
        'graphs': {
            'ccs': plot_hourly_climbing_scores(model, adapted, destination).to_json(),
            'temperature': plot_hourly_temp(model, adapted, destination).to_json(),
            'humidity': plot_hourly_humidity(model, adapted, destination).to_json()
        }
    })


if __name__ == '__main__':
    application.run()
