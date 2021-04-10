"""Build the web application."""
import os

from flask import Flask

from . import computer_facts


def create_app() -> Flask:
    """Make the application."""
    app = Flask(__name__)
    app.register_blueprint(computer_facts.bp)
    return app
