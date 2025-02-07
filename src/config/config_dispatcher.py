from config.config import Config

configHelper = Config()


class ConfigDispatcher:
    def __init__(self, cl_config: Config = None):
        self.max_msg_len = 50000
        self.alive_message = 24

        self.apprise_enable = True
        self.apprise_configs = []

        if cl_config is not None:
            self.__init_configuration_app__(cl_config)

    def __print_configuration__(self):
        """
        Print setup class
        """

        print(f"ConfigDispatcher {self.apprise_configs}")

    def __init_configuration_app__(self, cl_config: Config):
        """
        Init configuration class reading from Config Helper
        Init configuration class reading from Config Helper
        """
        # global
        self.alive_message = cl_config.notification_alive_message_hours()
        self.apprise_configs = configHelper.get_apprise_config()

        # print
        self.__print_configuration__()
