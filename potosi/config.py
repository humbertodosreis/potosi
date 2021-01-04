from os import path

from dynaconf import Dynaconf

settings = Dynaconf(load_dotenv=True, envvar_prefix="APP")
settings.ROOT_PATH = path.abspath(path.join(path.dirname(__file__), ".."))
