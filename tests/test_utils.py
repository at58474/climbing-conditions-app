import pytest
from weather_app.utils import calculate_dew_point, calculate_climbing_conditions_score

class DummyModel:
    def predict(self, X):
        return [sum(x) / len(x) for x in X]  # simple average for testing

def test_calculate_dew_point():
    assert calculate_dew_point(70, 50) == 70 - ((100 - 50) / 5.0)

def test_calculate_climbing_conditions_score_same_temp_and_dew():
    model = DummyModel()
    score = calculate_climbing_conditions_score(model, 70, 50, 70)
    assert 0 <= score

def test_calculate_climbing_conditions_score_dew_diff():
    model = DummyModel()
    score = calculate_climbing_conditions_score(model, 60, 50, 70)
    assert 0 <= score
