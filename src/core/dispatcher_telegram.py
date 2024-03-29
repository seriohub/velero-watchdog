import asyncio
import requests
from datetime import datetime

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_async_method
from utils.strings import ClassString


config_app = Config()

class DispatcherTelegram:
    """
    Provide a wrapper for sending data over Telegram
    """

    def __init__(self,
                 queue=None,
                 dispatcher_config: ConfigDispatcher = None,
                 k8s_key_config: ConfigK8sProcess = None):

        self.print_helper = PrintHelper('[core.dispatcher_telegram]',
                                        level=config_app.get_internal_log_level())

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.queue = queue

        self.telegram_api_token = dispatcher_config.telegram_token
        self.telegram_chat_ID = dispatcher_config.telegram_chat_id
        self.telegram_enable = dispatcher_config.telegram_enable
        self.telegram_max_msg_len = dispatcher_config.telegram_max_msg_len
        self.telegram_rate_minute = dispatcher_config.telegram_rate_limit

        self.telegram_last_minute = 0
        self.telegram_last_rate = 0

        # init class string
        self.class_strings = ClassString()

    @handle_exceptions_async_method
    async def __can_send_message__(self):
        """
        Check if the rate limit for the current time is reached
        """
        try:
            self.print_helper.info(f"__can_send_message__"
                                   f"{self.telegram_last_rate}/{self.telegram_rate_minute}")
            self.telegram_last_rate += 1
            seconds_waiting = 0
            while True:
                my_data = datetime.now()
                if my_data.minute != self.telegram_last_minute:
                    self.telegram_last_minute = my_data.minute
                    self.telegram_last_rate = 0

                if self.telegram_last_rate <= self.telegram_rate_minute:
                    break
                if seconds_waiting % 30 == 0:
                    self.print_helper.info(f"...wait {60 - my_data.second} seconds. "
                                           f"Max rate minute reached {self.telegram_rate_minute}")

                await asyncio.sleep(1)
                seconds_waiting += 1

        except Exception as err:
            self.print_helper.error_and_exception(f"__can_send_message__", err)

    @handle_exceptions_async_method
    async def send_to_telegram(self, message):
        """
        Send message to telegram
        @param message: body message
        """
        self.print_helper.info(f"send_to_telegram")
        await self.__can_send_message__()
        if self.telegram_enable:
            if len(self.telegram_api_token) > 0 and len(self.telegram_chat_ID) > 0:
                api_url = f'https://api.telegram.org/bot{self.telegram_api_token}/sendMessage'
                try:

                    response = requests.post(api_url, json={'chat_id': self.telegram_chat_ID,
                                                            'text': message})
                    self.print_helper.info(f"send_to_telegram.response {response.text[1:10]}")

                except Exception as e:
                    self.print_helper.error_and_exception(f"send_to_telegram", e)
            else:
                if len(self.telegram_api_token) == 0:
                    self.print_helper.error(f"send_to_telegram. api token is not defined")
                if len(self.telegram_chat_ID) == 0:
                    self.print_helper.error(f"send_to_telegram. chatID is not defined")
        else:
            self.print_helper.info(f"send_to_telegram[Disable send...only std out]=\n{message}")

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        main loop
        """
        try:
            self.print_helper.info(f"telegram channel notification is active")
            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                self.print_helper.info(f"telegram channel: new element received")

                if item is not None:
                    messages = self.class_strings.split_string(item,
                                                               self.telegram_max_msg_len, '\n')
                    for message in messages:
                        await self.send_to_telegram(message)

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
