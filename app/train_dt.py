import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'decision_tree_regression_model.pkl')
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'climbing_conditions_data_v2.xlsx')


def load_training_data(path=DATA_PATH):
    df = pd.read_excel(path)
    temperature = df["Temperature"].tolist()
    humidity = df["Humidity"].tolist()
    values = df["Values"].tolist()
    return list(zip(temperature, humidity, values))


def train_decision_tree_regression(data, save_model=True, model_path=MODEL_PATH):
    features = [(temp, humid) for temp, humid, _ in data]
    labels = [ccs for _, _, ccs in data]

    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

    dt = DecisionTreeRegressor(random_state=42)
    dt.fit(X_train, y_train)

    y_pred = dt.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    if save_model:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(dt, model_path)

    return dt, mse, r2


def load_decision_tree_model(model_path=MODEL_PATH):
    if os.path.exists(model_path):
        return joblib.load(model_path)
    else:
        return None


def get_or_train_model():
    model = load_decision_tree_model()
    if model is None:
        data = load_training_data()
        model, mse, r2 = train_decision_tree_regression(data, save_model=True)
        print(f"Model trained. MSE: {mse:.3f}, R²: {r2:.3f}")
    return model
