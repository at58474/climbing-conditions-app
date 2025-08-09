from weather_app.plot_utils import process_hourly_data

class DummyModel:
    def predict(self, X):
        return [7.0 for _ in X]

def test_process_hourly_data_returns_expected_format():
    dummy_data = [
        {
            "dt": 1691232000,
            "main": {"temp": 75, "humidity": 50, "dew_point": 55},
            "weather": [{"id": 800}],
            "pop": 0.2,
            "wind": 5,
            "rain_accumulation": 0.1
        }
    ]
    x, y, colors, labels, hover = process_hourly_data(dummy_data, DummyModel(), "score")
    assert isinstance(x, list)
    assert len(x) == len(dummy_data)