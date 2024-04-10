from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_async_method
import requests
import json

config_app = Config()


class DispatcherSlack:
    """
    Provide a wrapper for sending data over slack channel
    """

    def __init__(self,
                 queue=None,
                 dispatcher_config: ConfigDispatcher = None,
                 k8s_key_config: ConfigK8sProcess = None):

        self.print_helper = PrintHelper('[core.dispatcher_slack]',
                                        level=config_app.get_internal_log_level())

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.dispatcher_config = ConfigDispatcher()
        if dispatcher_config is not None:
            self.dispatcher_config = dispatcher_config

        self.queue = queue

    @handle_exceptions_async_method
    async def send_slack_message(self, message):
        """
        Send slack message func
        @param message: body message
        """
        try:
            self.print_helper.info(f"send_slack")
            if (len(self.dispatcher_config.slack_channel) > 0 and
                    len(self.dispatcher_config.slack_token) > 0):
                url = "https://slack.com/api/chat.postMessage"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.dispatcher_config.slack_token}"
                }

                data = {
                    "channel": self.dispatcher_config.slack_channel,
                    "text": message
                }

                response = requests.post(url, headers=headers, data=json.dumps(data))

                if response.status_code == 200:
                    self.print_helper.info(f"Message sent successfully to Slack channel "
                                           f"{self.dispatcher_config.slack_channel}")
                else:
                    self.print_helper.error(f"Failed to send message. Error: {response.status_code} - {response.text}")
            else:
                self.print_helper.error(f"Failed to send message. settings missed")

        except Exception as err:
            self.print_helper.error_and_exception(f"send_slack_message", err)

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        Main loop
        """
        try:
            self.print_helper.info(f"slack channel notification is active")
            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                self.print_helper.debug(f"slack channel: new element received")

                if item is not None and len(item) > 0:
                    await self.send_slack_message(item)

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
