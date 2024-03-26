from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from passlib.hash import sha256_crypt
import pymysql.cursors
import requests
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
from climbing_conditions import fetch_hourly_weather_data, plot_hourly_climbing_scores, calculate_climbing_conditions_score
import logging

app = Flask(__name__)

# MySQL configurations
DB_HOST = 'route-database.cnkg64eooql0.us-east-2.rds.amazonaws.com'
DB_USER = 'at58474'
DB_PASSWORD = 'Azsxdcfv12!'
DB_NAME = 'route_schema'

# Secret key for session management
app.secret_key = 'tux'


# Function to connect to MySQL database
def connect_to_database():
    return pymysql.connect(host=DB_HOST,
                           user=DB_USER,
                           password=DB_PASSWORD,
                           db=DB_NAME,
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/graph')
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


# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Validate input fields
        if not name or not email or not password:
            error = 'Please fill out all the fields.'
            return render_template('register.html', error=error)

        # Hash the password
        password_hash = sha256_crypt.encrypt(password)

        connection = connect_to_database()
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
                cursor.execute(sql, (name, email, password_hash))
                connection.commit()
        finally:
            connection.close()

        return redirect(url_for('login'))
    return render_template('register.html')


# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password']

        connection = connect_to_database()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s"
                cursor.execute(sql, (email,))
                user = cursor.fetchone()
                if user:
                    password = user['password']
                    if sha256_crypt.verify(password_candidate, password):
                        session['logged_in'] = True
                        session['email'] = email
                        return redirect(url_for('submit_info'))
                    else:
                        error = 'Invalid login'
                        return render_template('login.html', error=error)
                else:
                    error = 'Email not found'
                    return render_template('login.html', error=error)
        finally:
            connection.close()
    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Form submission route
@app.route('/submit_info', methods=['GET', 'POST'])
def submit_info():
    if request.method == 'POST':
        if 'logged_in' in session:
            route_name = request.form['route_name']
            route_angle = request.form['route_angle']
            route_grade = request.form['route_grade']

            print("Route Name:", route_name)
            print("Route Angle:", route_angle)
            print("Route Grade:", route_grade)

            # Print all form data received
            print("All Form Data:", request.form)

            connection = connect_to_database()
            try:
                with connection.cursor() as cursor:
                    # Insert data into routes table
                    cursor.execute("INSERT INTO routes (route_name, route_angle, route_grade) VALUES (%s, %s, %s)",
                                   (route_name, route_angle, route_grade))
                    route_id = cursor.lastrowid

                    # Insert data into moves table for each move
                    move_count = int(request.form.get('move_count', 0))
                    print("Move Count:", move_count)
                    for i in range(1, move_count + 1):
                        move_size = request.form[f'move_size_{i}']
                        move_modifier = request.form[f'move_modifier_{i}']
                        move_modifier_secondary = request.form[f'move_modifier_secondary_{i}']
                        move_modifier_tertiary = request.form[f'move_modifier_tertiary_{i}']

                        # Insert data into moves table
                        cursor.execute(
                            "INSERT INTO moves (route_id, move_size, move_modifier, move_modifier_secondary, move_modifier_tertiary) VALUES (%s, %s, %s, %s, %s)",
                            (route_id, move_size, move_modifier, move_modifier_secondary, move_modifier_tertiary))
                        move_id = cursor.lastrowid

                        # Insert data into holds table for each hold
                        hold_type = request.form.get(f'hold_type_{i}')
                        secondary_hold_type = request.form.get(f'secondary_hold_type_{i}')  # Corrected field name
                        hold_direction = request.form.get(f'hold_direction_{i}')
                        hold_size = request.form.get(f'hold_size_{i}')
                        hold_width = request.form.get(f'hold_width_{i}')

                        # Insert data into holds table
                        cursor.execute(
                            "INSERT INTO holds (move_id, hold_type, secondary_hold_type, hold_direction, hold_size, hold_width) VALUES (%s, %s, %s, %s, %s, %s)",
                            (move_id, hold_type, secondary_hold_type, hold_direction, hold_size, hold_width))

                    connection.commit()
            finally:
                connection.close()
            return 'Information submitted successfully'
        else:
            return redirect(url_for('login'))
    return render_template('submit_info.html')



# Add logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/current_conditions')
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
    app.run(debug=True)