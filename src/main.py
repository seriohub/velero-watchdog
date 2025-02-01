import uvicorn
import sys

from config.config import Config

from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()

logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))

logger.info("Watchdog starting...")
logger.info("Loading config...")

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
                reload=True,
                # log_level=log_level,
                workers=2,
                )
