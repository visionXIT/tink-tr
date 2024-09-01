import logging

from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv(".env")


class Settings(BaseSettings):
    app_name: str = "qwertyo21"
    token: str
    account_id: str
    password: str = "2"
    sandbox: bool = False
    log_level = logging.DEBUG
    tinkoff_library_log_level = logging.INFO

    class Config:
        env_file = ".env"


settings = Settings()
