import os
import joblib
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'random_forest_regression_model.pkl')
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'climbing_conditions_data_v2.db')


def load_training_data(db_path=DB_PATH):
    """Load training data from SQLite database."""
    conn = sqlite3.connect(db_path)
    query = 'SELECT Temperature, Humidity, "Values" FROM climbing_conditions_data_v2'
    df = pd.read_sql_query(query, conn)
    conn.close()

    temperature = df["Temperature"].tolist()
    humidity = df["Humidity"].tolist()
    values = df["Values"].tolist()
    return list(zip(temperature, humidity, values))


def train_random_forest_regression(data, save_model=True, model_path=MODEL_PATH):
    features = [(temp, humid) for temp, humid, _ in data]
    labels = [ccs for _, _, ccs in data]

    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    if save_model:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(rf, model_path)

    return rf, mse, r2


def load_random_forest_model(model_path=MODEL_PATH):
    if os.path.exists(model_path):
        return joblib.load(model_path)
    else:
        return None


def get_or_train_model():
    model = load_random_forest_model()
    if model is None:
        data = load_training_data()
        model, mse, r2 = train_random_forest_regression(data, save_model=True)
        print(f"Model trained. MSE: {mse:.3f}, R²: {r2:.3f}")
    return model
