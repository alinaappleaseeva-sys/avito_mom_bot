from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///avito_bot.db"
    
    # Avito Config
    AVITO_API_MODE: str = "mock" # "mock", "real" or "sandbox"
    AVITO_CLIENT_ID: str = ""
    AVITO_CLIENT_SECRET: str = ""
    AVITO_USER_ID: str = ""
    TELEGRAM_ADMIN_ID: int = 0
    
    # WebApp Auth
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
