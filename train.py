import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score

# Read the Excel file
df = pd.read_excel("ClimbingConditionsTrain DT.xlsx")

# Extract Temperature, Humidity, and Values columns
temperature = df["Temperature"].tolist()
humidity = df["Humidity"].tolist()
values = df["Values"].tolist()

# Combine the lists into a list of tuples (temperature, humidity, value)
data = list(zip(temperature, humidity, values))

# Print the first few entries to verify
print(data[:5])


def train_decision_tree_regression(data, save_model=True):
    # Extracting features (Temperature and Humidity) and labels (Condition) from the data
    features = [(temp, humid) for temp, humid, _ in data]
    labels = [condition for _, _, condition in data]

    # Splitting the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

    # Initializing and training the decision tree regressor
    clf = DecisionTreeRegressor()
    clf.fit(X_train, y_train)

    # Predicting the labels for the test set
    y_pred = clf.predict(X_test)

    # Calculating the mean squared error of the model
    mse = mean_squared_error(y_test, y_pred)

    # Calculating the R^2 score of the model
    r2 = r2_score(y_test, y_pred)

    if save_model:
        # Save the trained model to disk
        joblib.dump(clf, 'decision_tree_regression_model.pkl')

    # Returning the trained model, mean squared error, and R^2 score
    return clf, mse, r2


def load_decision_tree_regression_model():
    # Load the trained model from disk
    return joblib.load('decision_tree_regression_model.pkl')


# Check if the trained model exists on disk
if not os.path.exists('decision_tree_regression_model.pkl'):
    # If the model doesn't exist, train it and save it to disk
    model, _, _ = train_decision_tree_regression(data)
else:
    # If the model exists, load it from disk
    model = load_decision_tree_regression_model()