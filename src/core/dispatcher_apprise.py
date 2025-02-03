import apprise

from config.config import Config
from config.config_dispatcher import ConfigDispatcher

from utils.handle_error import handle_exceptions_async_method
from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()
logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))


class DispatcherApprise:
    """
    Provide a wrapper for sending data
    """

    def __init__(self,
                 queue=None,
                 dispatcher_config: ConfigDispatcher = None,
                 test_configs=None
                 ):

        self.dispatcher_config = dispatcher_config

        self.queue = queue
        self.apobj = apprise.Apprise()

        if not test_configs:
            self.load_config()
        else:
            # Adding configurations to the Apprise object
            self.apobj.add(test_configs)

    def load_config(self):
        notification_configs = self.dispatcher_config.apprise_configs

        self.apobj.clear()
        # Adding configurations to the Apprise object
        for config in notification_configs:
            try:
                self.apobj.add(config)
            except Exception as e:
                print(f"Error in adding configuration '{config}': {e}")

    async def load_apprise_configs(self):
        self.load_config()

    @handle_exceptions_async_method
    async def send_msgs(self, message, test_message=False):
        """
        Send message
        @param message: body message
        @param test_message: bool true if test message, false otherwise
        """
        try:
            if len(self.apobj) == 0:
                logger.error("No APPRISE config found")
            # Iteration on services to send notifications individually and catch errors.
            for service in self.apobj:
                success = False
                try:
                    logger.info(f"Try sent message to {service}")
                    # Send notification
                    success = service.notify(
                        body=message,
                        title="Vui Watchdog",
                    )
                    if success:
                        logger.info(f"Notification sent with success: {service.url()}")

                    else:
                        logger.error(f"Error in sending notification: {service.url()}")
                except Exception as e:
                    logger.error(f"Error in sending notification {service.url()}: {str(e)}")
                finally:
                    if test_message:
                        return success

        except Exception as err:
            logger.error(f"Error APPRISE sending notification {str(err)}")

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        Main loop
        """
        try:

            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                logger.info("APPRISE dispatcher: new element received")
                logger.debug(f"APPRISE dispatcher: new element received"
                             "\n--------------------------------------------------------------------------------------"
                             f"\n{str(item)}"
                             f"\n-------------------------------------------------------------------------------------")

                if item is not None and len(item) > 0:
                    await self.send_msgs(item)

        except Exception as err:
            logger.error(f"run {str(err)}")
