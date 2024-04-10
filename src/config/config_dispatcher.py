from config.config import Config


class ConfigDispatcher:
    def __init__(self, cl_config: Config = None):
        self.max_msg_len = 50000
        self.alive_message = 24

        self.telegram_enable = False
        self.telegram_chat_id = '0'
        self.telegram_token = ''
        self.telegram_max_msg_len = 2000
        self.telegram_rate_limit = 20

        self.email_enable = True
        self.email_smtp_server = ''
        self.email_smtp_port = 587
        self.email_sender = ''
        self.email_sender_password = '***'
        self.email_recipient = ''

        self.slack_enable = True
        self.slack_channel = ''
        self.slack_token = ''

        if cl_config is not None:
            self.__init_configuration_app__(cl_config)

    def __mask_data__(self, data):
        if len(data) > 2:
            index = int(len(data) / 2)
            partial = '*' * index
            return f"{self.telegram_token[:index]}{partial}"
        else:
            return data

    def __print_configuration__(self):
        """
        Print setup class
        """

        print(f"INFO    [Dispatcher setup] telegram={self.telegram_enable}")
        if self.telegram_enable:
            print(f"INFO    [Dispatcher setup] telegram-chat id={self.telegram_chat_id}")
            print(f"INFO    [Dispatcher setup] telegram-token={self.__mask_data__(self.telegram_token)}")
            print(f"INFO    [Dispatcher setup] telegram-max message length={self.telegram_max_msg_len}")
            print(f"INFO    [Dispatcher setup] telegram-rate limit minute={self.telegram_rate_limit}")
            print(f"INFO    [Dispatcher setup] Notification-alive message every={self.alive_message} hour")

        print(f"INFO    [Dispatcher setup] email={self.email_enable}")
        if self.email_enable:
            print(f"INFO    [Dispatcher setup] email-smtp server={self.email_smtp_server}")
            print(f"INFO    [Dispatcher setup] email-port={self.email_smtp_port}")
            print(f"INFO    [Dispatcher setup] email-sender={self.email_sender}")
            # print(f"INFO    [Dispatcher setup] email-password={self.__mask_data__(self.email_sender_password)}")
            print(f"INFO    [Dispatcher setup] email-password={self.email_sender_password}")
            print(f"INFO    [Dispatcher setup] email-recipient={self.email_recipient}")

        print(f"INFO    [Dispatcher setup] Slack={self.slack_enable}")
        if self.telegram_enable:
            print(f"INFO    [Dispatcher setup] slack-channel id={self.slack_channel}")
            print(f"INFO    [Dispatcher setup] slack-token={self.__mask_data__(self.slack_token)}")

    def __init_configuration_app__(self, cl_config: Config):
        """
        Init configuration class reading .env file
        """
        # global
        self.alive_message = cl_config.notification_alive_message_hours()

        # telegram section
        self.telegram_enable = cl_config.telegram_enable()
        self.telegram_chat_id = cl_config.telegram_chat_id()
        self.telegram_token = cl_config.telegram_token()
        self.telegram_max_msg_len = cl_config.telegram_max_msg_len()
        self.telegram_rate_limit = cl_config.telegram_rate_limit_minute()

        # email
        self.email_enable = cl_config.email_enable()
        self.email_sender = cl_config.email_sender()
        self.email_sender_password = cl_config.email_sender_password()
        self.email_smtp_port = cl_config.email_smtp_port()
        self.email_smtp_server = cl_config.email_smtp_server()
        self.email_recipient = cl_config.email_recipient()

        # slack
        self.slack_enable = cl_config.slack_enable()
        self.slack_channel = cl_config.slack_channel_id()
        self.slack_token = cl_config.slack_token()

        # print
        self.__print_configuration__()