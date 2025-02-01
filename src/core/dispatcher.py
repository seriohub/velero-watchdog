from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from utils.handle_error import handle_exceptions_async_method

from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()
logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))


class Dispatcher:
    """
    Provide a wrapper for sending data over different channels
    """

    def __init__(self,
                 queue=None,
                 queue_dispatcher_apprise=None,
                 # queue_telegram=None,
                 # queue_mail=None,
                 # queue_slack=None,
                 dispatcher_config: ConfigDispatcher = None,
                 k8s_key_config: ConfigK8sProcess = None):

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.dispatcher_config = ConfigDispatcher()
        if dispatcher_config is not None:
            self.dispatcher_config = dispatcher_config

        self.queue = queue
        self.queue_dispatcher_apprise = queue_dispatcher_apprise

    @handle_exceptions_async_method
    async def __put_in_queue__(self,
                               queue,
                               obj):
        """
        Add new element to the queue
        :param queue: reference to a queue
        :param obj: object to add in the queue
        """
        # self.print_helper.debug("__put_in_queue__")

        await queue.put(obj)

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        main loop.
        @return:
        """
        try:
            logger.info(f"Dispatcher RUN active")
            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                if item is None:
                    logger.warning(f"dispatcher new receive element: item is None")
                    break

                logger.debug(f"dispatcher new receive element: {item}")
                # if len(item) < 20:
                #     self.print_helper.debug(f"dispatcher new receive len(element)<20 item: {str(item)}")
                #     break

                if item is not None and len(item) > 0:
                    if self.dispatcher_config.apprise_enable:
                        await self.__put_in_queue__(self.queue_dispatcher_apprise,
                                                    item)
                    else:
                        logger.warning(f"No APPRISE config found. Only std out]=\n{item}")
                else:
                    logger.error(f"send_to_std_out[item len 0]=\n{item}")

        except Exception as err:
            logger.error(f"run {str(err)}")
