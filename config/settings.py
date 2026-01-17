import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    """
    Central configuration for the application.

    This class loads environment variables from a .env file and exposes them
    as typed attributes. It serves as a singleton source of truth for configuration
    settings across the entire application.

    Attributes:
        PROJECT_NAME (str): The name of the project. Defaults to "AI Code Reviewer".
        VERSION (str): The current version of the application.
        ENV (str): The current operating environment (e.g., 'development', 'production').
        DEBUG (bool): True if running in development mode, False otherwise.
        LOG_LEVEL (str): The logging level (e.g., 'DEBUG', 'INFO'). Defaults to 'INFO'.
        API_HOST (str): The host address for the API server.
        API_PORT (int): The port number for the API server. Defaults to 8000.
        ROOT_DIR (Path): The absolute path to the project root directory.
        SRC_DIR (Path): The absolute path to the source code directory.
    """

    # Project info
    PROJECT_NAME : str = os.getenv("PROJECT_NAME", "AI Code Reviewer")

    VERSION: str = "0.1.0"

    # Environtment 
    ENV : str = os.getenv("FLASK_ENV " , "development")
    DEBUG : bool = ENV == "development"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL" , "INFO").upper()


    # API Config
    API_HOST : str="0.0.0.0"
    API_PORT :int = int(os.getenv("API_PORT" , 8000))

    #Paths
    ROOT_DIR: Path = BASE_DIR
    SRC_DIR: Path = BASE_DIR/"src"

settings= Settings()