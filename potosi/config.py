from os import path

from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=["settings.toml"],
    environments=True,
    load_dotenv=True,
    envvar_prefix="APP",
    validator=[
        Validator(
            "DATABASE_URI",
            "TELEGRAM_API_ID",
            "TELEGRAM_API_HASH",
            "BINANCE_API_KEY",
            "APP_BINANCE_API_SECRET",
            "USER_INPUT_CHANNEL",
            must_exist=True,
        )
    ],
)
settings.ROOT_PATH = path.abspath(path.join(path.dirname(__file__), ".."))
