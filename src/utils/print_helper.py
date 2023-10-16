import os
import logging
from logging.handlers import RotatingFileHandler


class LLogger:
    def __init__(self):
        self.logger = None

    def init_logger(self,
                    key,
                    output_format,
                    save_to_file,
                    destination_folder,
                    filename,
                    max_file_size,
                    historical_files,
                    level):
        if self.logger is None:

            logging.basicConfig(format=output_format,
                                level=level)
            self.logger = logging.getLogger(key)
            if save_to_file:
                print("INFO    logger folder files {0}".format(filename))
                file_to_log = os.path.join(destination_folder, filename)
                handler = RotatingFileHandler(file_to_log,
                                              maxBytes=max_file_size,
                                              backupCount=historical_files)
                formatter = logging.Formatter(output_format)
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

            # self.logger.setLevel(logging.DEBUG)

        return self.logger

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PrintHelper:

    def __init__(self, namespace, logger=None):
        self.msg_len = 10
        self.logger_enable = False
        self.logger = None
        self.set_logger(logger)
        self.name = namespace

    def set_logger(self, logger):
        self.logger = logger
        if self.logger is not None:
            self.logger_enable = True

    def debug_if(self, enable=True, msg=''):
        if enable:
            if self.logger_enable:
                message = f"{bcolors.OKCYAN}{self.name} {msg}{bcolors.ENDC}"
                self.logger.debug(message)
            else:
                self.debug(msg)

    def debug(self, msg):

        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.debug(message)
        else:
            title = "DEBUG:"
            print(f"{bcolors.OKCYAN}{title.ljust(self.msg_len, ' ')}{self.name} {msg}{bcolors.ENDC}")

    def highlights(self, msg):
        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.info(message)
        else:
            title = "INFO:"
            # print(f"DEBUG:    {self.name} {msg}")
            print(f"{bcolors.OKGREEN}{title.ljust(self.msg_len, ' ')}{self.name} {msg}{bcolors.ENDC}")

    def info_if(self, enable=True, msg=''):
        if enable:
            if self.logger_enable:
                message = f"{self.name} {msg}"
                self.logger.info(message)
            else:
                self.info(msg)

    def info(self, msg):
        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.info(message)
        else:
            title = "INFO:"
            print(f"{title.ljust(self.msg_len, ' ')}{self.name} {msg}")

    def wrn(self, msg):
        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.warning(message)
        else:
            title = "WARNING:"
            print(f"{bcolors.WARNING}{title.ljust(self.msg_len, ' ')}{self.name} {msg}{bcolors.ENDC}")

    def alert(self, msg):
        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.fatal(message)
        else:
            title = "ALERT:"
            print(f"{bcolors.BOLD}{title.ljust(self.msg_len, ' ')}{self.name} {msg}{bcolors.ENDC}")

    def error(self, msg):
        if self.logger_enable:
            message = f"{self.name} {msg}"
            self.logger.error(message)
        else:
            title = "ERROR:"
            print(f"{bcolors.FAIL}{title.ljust(self.msg_len, ' ')}{self.name} {msg}{bcolors.ENDC}")
