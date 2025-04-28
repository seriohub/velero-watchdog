import os
import uvicorn
import sys

from config.config import Config , get_configmap, get_secret_parameter

from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()

logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))

logger.info("Watchdog System starting...")
logger.info("Loading config...")


def load_user_config():

    print("\nAdd user configs environment")
    cm = get_configmap(namespace=os.getenv('K8S_VELERO_UI_NAMESPACE', 'velero-ui'),
                       configmap_name='velero-watchdog-user-config')
    if cm:
        # Update environment variables
        for key, value in cm.items():
            print("Loading user config: Adding", key, value)
            os.environ[key] = value

    apprise = get_secret_parameter(namespace=os.getenv('K8S_VELERO_UI_NAMESPACE', 'velero-ui'),
                                   secret_name='velero-watchdog-user-config', parameter="APPRISE")

    if apprise:
        print("Loading user secret: Adding APPRISE.....")
        os.environ["APPRISE"] = apprise


load_user_config()

if __name__ == '__main__':
    daemon = False
    if len(sys.argv) > 1 and '--daemon' in sys.argv:
        daemon = True

    endpoint_url = config_app.get_endpoint_url()
    endpoint_port = config_app.get_endpoint_port()

    logger.info(f"Run server at url:{endpoint_url}-port={endpoint_port}")

    uvicorn.run('app:app',
                host=endpoint_url,
                port=int(endpoint_port),
                reload=config_app.uvicorn_reload_update(),
                # log_level=log_level,
                workers=1,
                )
