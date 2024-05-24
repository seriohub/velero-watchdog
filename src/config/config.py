import os
from dotenv import load_dotenv, find_dotenv
from dotenv.main import dotenv_values

from utils.handle_error import handle_exceptions_method


# class syntax
class Config:
    def __init__(self, path_env=None):
        load_dotenv(dotenv_path=path_env)

    @staticmethod
    def load_key(key, default, print_out: bool = True, mask_value: bool = False):
        value = os.getenv(key)
        if value is None or \
                len(value) == 0:
            value = default

        if print_out:
            if mask_value and len(value) > 2:
                index = int(len(value) / 2)
                partial = '*' * index
                print(f"INFO    [Env] load_key.key={key} value={value[:index]}{partial}")
            else:
                print(f"INFO    [Env] load_key.key={key} value={value}")

        return value

    @handle_exceptions_method
    def logger_key(self):
        return self.load_key('LOG_KEY', 'k8s-wdt')

    @handle_exceptions_method
    def logger_msg_format(self):
        default = '%(asctime)s :: [%(levelname)s] :: %(message)s'
        return self.load_key('LOG_FORMAT', default)

    @handle_exceptions_method
    def logger_save_to_file(self):
        res = self.load_key('LOG_SAVE', 'False')
        return True if res.upper() == 'TRUE' else False

    @handle_exceptions_method
    def logger_folder(self):
        return self.load_key('LOG_DEST_FOLDER',
                             './logs')

    @handle_exceptions_method
    def logger_filename(self):
        return self.load_key('LOG_FILENAME',
                             'k8s.log')

    @handle_exceptions_method
    def logger_max_filesize(self):
        return int(self.load_key('LOG_MAX_FILE_SIZE',
                                 4000000))

    @handle_exceptions_method
    def logger_his_backups_files(self):
        return int(self.load_key('LOG_FILES_BACKUP',
                                 '5'))

    @handle_exceptions_method
    def logger_level(self):
        return int(self.load_key('LOG_LEVEL',
                                 '20'))

    @handle_exceptions_method
    def process_run_sec(self):
        res = self.load_key('PROCESS_CYCLE_SEC',
                            '120')

        if len(res) == 0:
            res = '120'
        return int(res)

    @handle_exceptions_method
    def internal_debug_enable(self):
        res = self.load_key('DEBUG', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def telegram_token(self):
        return self.load_key('TELEGRAM_TOKEN', '', mask_value=True)

    @handle_exceptions_method
    def telegram_chat_id(self):
        return self.load_key('TELEGRAM_CHAT_ID', '', mask_value=True)

    @handle_exceptions_method
    def telegram_enable(self):
        res = self.load_key('TELEGRAM_ENABLE', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def telegram_max_msg_len(self):
        res = self.load_key('TELEGRAM_MAX_MSG_LEN',
                            '3000')

        if len(res) == 0:
            res = '2000'
        return int(res)

    @handle_exceptions_method
    def telegram_rate_limit_minute(self):
        res = self.load_key('TELEGRAM_MAX_MSG_MINUTE',
                            '20')

        if len(res) == 0:
            res = '20'
        return int(res)

    @handle_exceptions_method
    def notification_alive_message_hours(self):
        res = self.load_key('NOTIFICATION_ALIVE_MSG_HOURS',
                            '24')
        n_hours = int(res)
        if n_hours < 0:
            n_hours = 0
        elif n_hours > 100:
            n_hours = 100

        return n_hours

    @handle_exceptions_method
    def email_enable(self):
        res = self.load_key('EMAIL_ENABLE', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def email_smtp_server(self):
        return self.load_key('EMAIL_SMTP_SERVER', '')

    @handle_exceptions_method
    def email_smtp_port(self):
        res = self.load_key('EMAIL_SMTP_PORT',
                            '587')
        n_port = int(res)
        return n_port

    @handle_exceptions_method
    def email_recipient(self):
        return self.load_key('EMAIL_RECIPIENTS', '')

    @handle_exceptions_method
    def email_sender_password(self):
        return self.load_key('EMAIL_PASSWORD', '', mask_value=True)

    @handle_exceptions_method
    def email_sender(self):
        return self.load_key('EMAIL_ACCOUNT', '')

    # LS 2024.04.10 add slack definition - BEGIN

    @handle_exceptions_method
    def slack_token(self):
        return self.load_key('SLACK_TOKEN', '', mask_value=True)

    @handle_exceptions_method
    def slack_channel_id(self):
        return self.load_key('SLACK_CHANNEL', '', mask_value=True)

    @handle_exceptions_method
    def slack_enable(self):
        res = self.load_key('SLACK_ENABLE', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

    # LS 2024.04.10 add slack definition - END

    @handle_exceptions_method
    def k8s_load_kube_config_method(self):
        res = self.load_key('PROCESS_LOAD_KUBE_CONFIG', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def k8s_config_file(self):
        return self.load_key('PROCESS_KUBE_CONFIG', None)

    @handle_exceptions_method
    def k8s_cluster_identification(self):
        return self.load_key('PROCESS_CLUSTER_NAME', None)

    @handle_exceptions_method
    def k8s_incluster_mode(self):
        res = self.load_key('K8S_INCLUSTER_MODE', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def velero_backup_enable(self):
        res = self.load_key('BACKUP_ENABLE', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def velero_schedule_enable(self):
        res = self.load_key('SCHEDULE_ENABLE', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def velero_expired_days_warning(self):
        res = self.load_key('EXPIRES_DAYS_WARNING',
                            '20')

        if len(res) == 0:
            res = '20'
        return int(res)

    @handle_exceptions_method
    def get_regex_patterns_ignore_nm(self):
        regex_list = []

        for i in range(1, 10):
            res = self.load_key(f'IGNORE_NM_{i}', None)
            if res is not None:
                # Append the regex pattern to the list
                # regex_list.append(re.compile(res))
                regex_list.append(res)
            else:
                break
        return regex_list

    @staticmethod
    def get_build_version():
        return os.getenv('BUILD_VERSION', 'dev')

    @staticmethod
    def get_date_build():
        return os.getenv('BUILD_DATE', '-')

    @staticmethod
    def get_endpoint_url():
        endpoint_url = os.getenv('API_ENDPOINT_URL')
        if endpoint_url is None or \
                len(endpoint_url) == 0:
            endpoint_url = '127.0.0.1'
        return endpoint_url

    @staticmethod
    def get_endpoint_port():
        endpoint_port = os.getenv('API_ENDPOINT_PORT')
        if endpoint_port is None or \
                len(endpoint_port) == 0:
            endpoint_port = '8001'
        return endpoint_port

    def get_internal_log_level(self):
        res = self.load_key('DEBUG_LEVEL', None)
        if res is not None:
            lev = res.lower()
            if lev in ['critical', 'error', 'warning', 'info', 'debug', 'trace', 'notset']:
                return lev

        return "info"

    @staticmethod
    def get_env_variables():
        data = dotenv_values(find_dotenv())
        kv = {}
        for k, v in data.items():
            if k.startswith('EMAIL_PASSWORD') or k.startswith('TELEGRAM_TOKEN'):
                v = v[0].ljust(len(v) - 1, '*')
                # print(temp)
                # v = temp
            kv[k] = v
        return kv

    def get_notification_skip_completed(self):
        res = self.load_key('NOTIFICATION_SKIP_COMPLETED', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    def get_notification_skip_inprogress(self):
        res = self.load_key('NOTIFICATION_SKIP_INPROGRESS', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    def get_notification_skip_removed(self):
        res = self.load_key('NOTIFICATION_SKIP_REMOVED', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    def get_notification_skip_deleting(self):
        res = self.load_key('NOTIFICATION_SKIP_DELETING', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    def get_report_backup_item_prefix(self):
        res = self.load_key('REPORT_BACKUP_ITEM_PREFIX', '')
        return res if res.lower() == '' else res + ' '

    def get_report_schedule_item_prefix(self):
        res = self.load_key('REPORT_SCHEDULE_ITEM_PREFIX', '')
        return res if res.lower() == '' else res + ' '

    @staticmethod
    def get_k8s_velero_namespace():
        return os.getenv('K8S_VELERO_NAMESPACE', 'velero')