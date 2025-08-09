from weather_app.forecast import generate_daily_forecast

class DummyModel:
    def predict(self, X):
        return [5.0] * len(X)

def test_generate_daily_forecast_basic():
    dummy_data = [
        {
            "dt": 1691232000,
            "main": {"temp": 75, "humidity": 50, "dew_point": 55},
            "pop": 0.2,
            "wind": 5,
            "rain_accumulation": 0.1
        }
    ]
    forecast = generate_daily_forecast(dummy_data, DummyModel())
    assert len(forecast) > 0
    assert "temp_low" in forecast[0]
    assert "ccs_low" in forecast[0]