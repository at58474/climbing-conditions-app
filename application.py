"""Climbing Conditions App routing file

Purpose: Since weather conditions have such a tremendous impact on climbing performance, the goal for this application
is to create a standardized score that can be used as a quick reference to assist in determining how the current and
forecasted weather will affect climbing ability. Secondary goals are to assist in understanding the differences that
exist between climbers, and also to help each individual climber understand how conditions affect their personal
performance.

This Flask app is deployed on AWS through Elastic Beanstalk at www.climbingconditions.com. Elastic Beanstalk manages
load balancing, scaling, and health monitoring. AWS Route 53 is the DNS service used for end-to-end routing over IPv6
and serves as the domain registrar for this app. AWS certificate manager is used for creating and managing the public
SSL certificate.

The following are the dependencies required for this application:
Flask==2.0.2
passlib==1.7.4
pymysql==1.0.2
requests==2.26.0
numpy==1.21.3
plotly==5.3.1

This Flask application routing file contains the following functions:

    * index() - routes base url to index template
    * graph() -
    * current_conditions() -
"""


from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from climbing_conditions import fetch_hourly_weather_data, plot_hourly_climbing_scores, calculate_climbing_conditions_score
import logging

application = Flask(__name__)


@application.route('/')
def index():
    return render_template('index.html')


def get_destination():
    # Climbing Conditions sidebar widget end user dropdown value
    destination = request.args.get('destination', '')

    # Dictionary of climbing destinations {Destination:Tuple} where the key is the climbing destination, and the
    #   value is a tuple that contains the city and country of the destination (City, Country)
    climbing_destinations = {
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

    # Checks to see if the selected destination is in the climbing_destination dictionary, if not then returns
    #   invalid destination, but if that's the case there is a discrepancy between this file and the html file.
    if destination in climbing_destinations:
        # Gets the city and country from the value of the dict which is a tuple
        city, country = climbing_destinations[destination]
        # openweathermap.org API key
        api_key = "59e23e27c5a507619213287828aca0bf"
        # calls fetch_hourly_weather_data function from climbing_conditions.py, which returns the hourly weather data
        #   then stores the data into hourly_data variable
        hourly_data = fetch_hourly_weather_data(api_key, city, country)
        # checks if hourly_data is populated, if so then stores the returned figure after calling
        #   plot_hourly_climbing_scores function from climbing_conditions.py
        if hourly_data:
            fig = plot_hourly_climbing_scores(hourly_data, city, destination)
            # converts the figure object into a plotly JSON string
            return hourly_data, city, destination
        else:
            return "Failed to fetch weather data"
    else:
        return "Invalid destination"


@application.route('/graph')
def graph():
    """Gets selected destination and then compares the destination to a dictionary of destinations {destination:city}.
    Stores the city and country into variables which are then used as parameters in the fetch_hourly_weather_data
    function call, along with the provided openweathermap.org API key. This function then calls the
    plot_hourly_climbing_scores function that displays the chart with the hourly data fetched from the weather API.

    Parameters
    ----------

    Returns
    -------
    JSON Figure
        the climbing conditions hourly plot that displays the CCS
    """

    hourly_data, city, destination = get_destination()

    fig = plot_hourly_climbing_scores(hourly_data, city, destination)
    # converts the figure object into a plotly JSON string
    return fig.to_json()


# Logging is used to track the events that occur in the current_conditions functions to reduce debugging time and to
#   ensure everything is working as expected.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@application.route('/current_conditions')
def current_conditions():
    """Just like in the graph() function above, this function gets the selected destination from request.args.get() and
    compares it to the same climbing_destinations{destination:(City,Country)} dictionary. The city, country, and api
    key are all set as in the last function.

    * Modify this file: create function that can be called that gets the selected destination, compares to dictionary,
    and then sets and returns the city, country, hourly_data, and api key. Make API key secure *

    This function then gets the humidity, dew point, and temperature from the hourly_data variable, which is the return
    from calling fetch_hourly_weather_data(). The calculate_climbing_conditions_score() function from
    climbing_conditions.py is then called and the returned CCSis stored in the score variable. The score is then rounded
    to the tenths, and the JSON response object is set and returned.


    Parameters
    ----------

    Returns
    -------
    flask.jsonify() response object, jsonify() is used since it sets response headers and content type automatically
        'temperature': temp_f,
        'humidity': humidity,
        'dew_point': dew_point_f,
        'climbing_conditions_score': rounded_score
    """

    hourly_data, city, destination = get_destination()

    # Retrieves the weather data for the current hour
    current_hour_data = hourly_data[0]
    logger.info(f"Received hourly data: {current_hour_data}")
    dew_point_f = current_hour_data['main']['feels_like']
    humidity = current_hour_data['main']['humidity']
    temp_f = current_hour_data['main']['temp']
    # Calls function to calculate CCS
    score = calculate_climbing_conditions_score(dew_point_f, humidity, temp_f)
    logger.info(f"Climbing conditions score calculated: {score}")

    # Calls the round() function to round the CCS to the tenths
    rounded_score = round(score, 1)

    # Creates a JSON response object that contains the temp, humidity, dew point, and CCS.
    response_data = {
        'temperature': temp_f,
        'humidity': humidity,
        'dew_point': dew_point_f,
        'climbing_conditions_score': rounded_score
    }

    # Using jsonify() rather than json.dumps() in a Flask app automatically sets the right response headers
    #   and content type
    return jsonify(response_data)


if __name__ == '__main__':
    application.run()
