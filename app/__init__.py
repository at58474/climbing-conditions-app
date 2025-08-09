from flask import Flask
import os
import joblib
# Change this to app.train_dt or app.train_rf depending on desired model
from app.train_rf import get_or_train_model
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

model = None  # Will be imported by routes

def create_app():
    app = Flask(__name__)

    # Load model at startup
    global model
    model = get_or_train_model()

    # Register routes
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
