from config.config import Config

config_app = Config()

__version__ = config_app.get_build_version()
__date__ = config_app.get_date_build()
