from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./AbhayaRaksha.db"
    GEMINI_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    SECRET_KEY: str = "changeme_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    class Config:
        env_file = ".env"

settings = Settings()
