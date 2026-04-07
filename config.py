from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///avito_bot.db"
    
    # Avito Config
    AVITO_CLIENT_ID: str = ""
    AVITO_CLIENT_SECRET: str = ""
    AVITO_USER_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
