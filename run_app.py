from shiny import run_app
import os

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(__file__), "app_shiny.py")
    run_app(app_path, launch_browser=True)