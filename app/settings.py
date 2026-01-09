from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env")


class Settings(BaseSettings):
    app_name: str = "qwertyo21"
    token: str
    account_id: str
    password: str = "2"
    sandbox: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
