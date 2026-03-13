import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MODEL = os.getenv("MODEL", "deepseek-coder:6.7b")
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 20))
    WORKSPACE = os.getenv("WORKSPACE", "workspace")
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.2))

settings = Settings()