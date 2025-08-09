import pytest
from unittest.mock import patch
from weather_app.weather_api import fetch_weather_data

@patch('weather_app.weather_api.requests.get')
def test_fetch_weather_data_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sample": "data"}

    api_key = "dummy"
    lat, lon = 35.0, -120.0
    data_2_5, data_3_0 = fetch_weather_data(api_key, lat, lon)

    assert data_2_5 is not None
    assert data_3_0 is not None