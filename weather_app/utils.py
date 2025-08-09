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