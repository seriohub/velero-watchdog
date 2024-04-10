from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_async_method


config_app = Config()

class Dispatcher:
    """
    Provide a wrapper for sending data over different channels
    """

    def __init__(self,
                 queue=None,
                 queue_telegram=None,
                 queue_mail=None,
                 queue_slack=None,
                 dispatcher_config: ConfigDispatcher = None,
                 k8s_key_config: ConfigK8sProcess = None):

        self.print_helper = PrintHelper('[core.dispatcher]',
                                        level=config_app.get_internal_log_level())

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.dispatcher_config = ConfigDispatcher()
        if dispatcher_config is not None:
            self.dispatcher_config = dispatcher_config

        self.queue = queue
        self.queue_telegram = queue_telegram
        self.queue_mail = queue_mail
        self.queue_slack = queue_slack

    @handle_exceptions_async_method
    async def __put_in_queue__(self,
                               queue,
                               obj):
        """
        Add new element to the queue
        :param queue: reference to a queue
        :param obj: object to add in the queue
        """
        self.print_helper.debug("__put_in_queue__")

        await queue.put(obj)

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        main loop.
        @return:
        """
        try:
            self.print_helper.info(f"dispatcher run active")
            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()
                # print(item)
                # check for stop signal
                if item is None:
                    break
                # LS 2024.04.10 temporary limit message length
                if len(item) < 20:
                    break
                self.print_helper.debug(f"dispatcher new receive element")

                if item is not None and len(item) > 0:
                    if self.dispatcher_config.telegram_enable:
                        await self.__put_in_queue__(self.queue_telegram,
                                                    item)
                    if self.dispatcher_config.email_enable:
                        await self.__put_in_queue__(self.queue_mail,
                                                    item)
                    if self.dispatcher_config.slack_enable:
                        await self.__put_in_queue__(self.queue_slack,
                                                    item)

                    if (not self.dispatcher_config.telegram_enable and
                            not self.dispatcher_config.email_enable and
                            not self.dispatcher_config.slack_enable):
                        self.print_helper.info(f"send_to_std_out[Disable send...only std out]=\n{item}")

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
