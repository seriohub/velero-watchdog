import os
from dotenv import load_dotenv, find_dotenv
from dotenv.main import dotenv_values

from utils.handle_error import handle_exceptions_method

from kubernetes import client, config
import base64


def get_configmap(namespace: str, configmap_name: str) -> {}:
    """
    Reads a specific parameter from a ConfigMap in Kubernetes.

    :param namespace: Namespace of the ConfigMap.
    :param configmap_name: Name of the ConfigMap.
    :return: Value of the parameter or None if the key does not exist.
    """
    # Load Kubernetes configuration
    try:
        config.load_incluster_config()  # Use cluster context if the app is running in the cluster.
    except config.ConfigException:
        config.load_kube_config()  # Use local kubeconfig file if running locally.

    # Initialize the API client
    v1 = client.CoreV1Api()

    try:
        # Read the specified ConfigMap.
        configmap = v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)

        # Returns the value of the parameter if it exists
        return configmap.data
    except client.exceptions.ApiException as e:
        # Handle errors, e.g. ConfigMap not found.
        if e.status == 404:
            print(f"ConfigHelper ConfigMap '{configmap_name}' not found in '{namespace}'.")
        else:
            print(f"ConfigHelper Error while reading the ConfigMap: {e}")
        return None


def get_configmap_parameter(namespace: str, configmap_name: str, parameter: str) -> str:
    """
    Reads a specific parameter from a ConfigMap in Kubernetes.

    :param namespace: Namespace of the ConfigMap.
    :param configmap_name: Name of the ConfigMap.
    :param parameter: Key of the parameter to be read.
    :return: Value of the parameter or None if the key does not exist.
    """
    # Load Kubernetes configuration
    try:
        config.load_incluster_config()  # Use cluster context if the app is running in the cluster.
    except config.ConfigException:
        config.load_kube_config()  # Use local kubeconfig file if running locally.

    # Initialize the API client
    v1 = client.CoreV1Api()

    try:
        # Read the specified ConfigMap.
        configmap = v1.read_namespaced_config_map(name=configmap_name, namespace=namespace)

        # Returns the value of the parameter if it exists
        return configmap.data.get(parameter, None)
    except client.exceptions.ApiException as e:
        # Handle errors, e.g. ConfigMap not found.
        if e.status == 404:
            print(f"ConfigHelper ConfigMap '{configmap_name}' not found in '{namespace}'.")
        else:
            print(f"ConfigHelper Error while reading the ConfigMap: {e}")
        return None


def get_secret_parameter(namespace: str, secret_name: str, parameter: str) -> str:
    """
    Reads a specific parameter from a Kubernetes Secret.

    :param namespace: The namespace where the Secret is located.
    :param secret_name: The name of the Secret.
    :param parameter: The key of the parameter to read.
    :return: The decoded value of the parameter, or None if the key does not exist.
    """
    # Load the Kubernetes configuration
    try:
        config.load_incluster_config()  # Use in-cluster config when running inside a Kubernetes cluster
    except config.ConfigException:
        config.load_kube_config()  # Use local kubeconfig when running outside the cluster

    # Initialize the CoreV1Api client
    v1 = client.CoreV1Api()

    try:
        # Retrieve the specified Secret
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)

        # Get the encoded value of the parameter if it exists
        encoded_value = secret.data.get(parameter, None)
        if encoded_value is not None:
            # Decode the base64-encoded value and return it as a string
            return base64.b64decode(encoded_value).decode("utf-8")
        return None
    except client.exceptions.ApiException as e:
        # Handle API exceptions (e.g., Secret not found)
        if e.status == 404:
            print(f"ConfigHelper Secret '{secret_name}' not found in namespace '{namespace}'.")
        else:
            print(f"ConfigHelper Error reading the Secret: {e}")
        return None


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
                print(f"ConfigHelper load_key.key={key} value={value[:index]}{partial}")
            else:
                print(f"ConfigHelper load_key.key={key} value={value}")

        return value

    def __load_user_bool_param(self, param, default_value):
        value = self.load_key(param, default_value)
        if value is not None:
            return True if value.lower() == "true" or value.lower() == "1" else False
        return None
        # local_user_config = self.load_key("LOCAL_USER_CONFIG", "False")
        # if local_user_config.lower() == 'true':
        #     res = self.load_key(param, default_value)
        #     return True if res.lower() == 'true' else False
        #
        # namespace = self.get_k8s_velero_ui_namespace()
        # configmap_name = "velero-watchdog-user-config"
        #
        # value = get_configmap_parameter(namespace, configmap_name, param)
        #
        # if value is not None:
        #     return True if value.lower() == "true" or value.lower() == "1" else False
        #
        # secret_name = "velero-watchdog-config"
        #
        # value = get_secret_parameter(namespace, secret_name, param)
        # if value is not None and value.strip() != '':
        #     return value.split(";")
        #
        # return default_value.lower() == 'true'

    def __load_user_param(self, param, default_value):
        return self.load_key(param, default_value)
        # local_user_config = self.load_key("LOCAL_USER_CONFIG", "False")
        # if local_user_config.lower() == 'true':
        #     res = self.load_key(param, default_value)
        #     return res
        #
        # namespace = self.get_k8s_velero_ui_namespace()
        # configmap_name = "velero-watchdog-user-config"
        #
        # value = get_configmap_parameter(namespace, configmap_name, param)
        #
        # if value is not None:
        #     return value
        #
        # configmap_name = "velero-watchdog-config"
        #
        # value = get_configmap_parameter(namespace, configmap_name, param)
        # if value is not None and value.strip() != '':
        #     return value
        #
        # return default_value

    #
    # logger config
    #

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
        return True if res.lower() == 'true' else False

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

    #
    # deploy config
    #

    @staticmethod
    def get_k8s_velero_namespace():
        return os.getenv('K8S_VELERO_NAMESPACE', 'velero')

    @staticmethod
    def get_k8s_velero_ui_namespace():
        return os.getenv('K8S_VELERO_UI_NAMESPACE', 'velero-ui')

    #
    # run app config
    #

    @handle_exceptions_method
    def internal_debug_enable(self):
        res = self.load_key('DEBUG', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

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

    #
    # k8s config
    #
    @handle_exceptions_method
    def k8s_load_kube_config_method(self):
        res = self.load_key('PROCESS_LOAD_KUBE_CONFIG', 'True')
        return True if res.lower() == "true" or res.lower() == "1" else False

    @handle_exceptions_method
    def k8s_config_file(self):
        return self.load_key('PROCESS_KUBE_CONFIG', None)

    @handle_exceptions_method
    def k8s_cluster_identification(self):
        return self.load_key('CLUSTER_ID', None)

    @handle_exceptions_method
    def k8s_incluster_mode(self):
        res = self.load_key('K8S_IN_CLUSTER_MODE', 'False')
        return True if res.lower() == "true" or res.lower() == "1" else False

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
        data = os.environ.copy()  # ✅ This reads the current environment variables.
        # data = dotenv_values()
        kv = {}
        for k, v in data.items():
            kv[k] = os.getenv(k, v)
        return kv

    #
    # user configs
    #

    @handle_exceptions_method
    def velero_schedule_enable(self):
        return self.__load_user_bool_param("SCHEDULE_ENABLED", "True")

    @handle_exceptions_method
    def velero_expired_days_warning(self):
        return int(self.__load_user_param("EXPIRES_DAYS_WARNING", 20))

    @handle_exceptions_method
    def velero_backup_enable(self):
        return self.__load_user_bool_param("BACKUP_ENABLED", "True")

    def get_report_schedule_item_prefix(self):
        return self.__load_user_param("REPORT_SCHEDULE_ITEM_PREFIX", "")

    def get_report_backup_item_prefix(self):
        return self.__load_user_param("REPORT_BACKUP_ITEM_PREFIX", "")

    def get_notification_skip_completed(self):
        return self.__load_user_bool_param("NOTIFICATION_SKIP_COMPLETED", "True")

    def get_notification_skip_inprogress(self):
        return self.__load_user_bool_param("NOTIFICATION_SKIP_INPROGRESS", "True")

    def get_notification_skip_removed(self):
        return self.__load_user_bool_param("NOTIFICATION_SKIP_REMOVED", "True")

    def get_notification_skip_deleting(self):
        return self.__load_user_bool_param("NOTIFICATION_SKIP_DELETING", "True")

    @handle_exceptions_method
    def process_run_sec(self):
        local_user_config = self.load_key("FORCE_LOCAL_PROCESS_CYCLE", "False")
        if local_user_config.lower() == 'true':
            res = self.load_key("FORCE_LOCAL_PROCESS_VALUE", 10)
            return int(res)
        return int(self.__load_user_param("PROCESS_CYCLE_SEC", 300))

    #
    # secret in velero-watchdog-app secret
    #

    def get_apprise_config(self):
        local_user_config = self.load_key("LOCAL_USER_CONFIG", "False")
        if local_user_config.lower() == 'true':
            res = self.load_key("APPRISE", "")
            return res.split(";")

        namespace = self.get_k8s_velero_ui_namespace()
        secret_name = "velero-watchdog-user-config"
        parameter = "APPRISE"

        value = get_secret_parameter(namespace, secret_name, parameter)
        if value is not None and value.strip() != '':
            return value.split(";")

        namespace = self.get_k8s_velero_ui_namespace()
        secret_name = "velero-watchdog-config"
        parameter = "APPRISE"

        value = get_secret_parameter(namespace, secret_name, parameter)
        if value is not None and value.strip() != '':
            return value.split(";")
        return []

    def send_start_message(self):
        return self.__load_user_bool_param("SEND_START_MESSAGE", "True")

    def send_report_at_startup(self):
        return self.__load_user_bool_param("SEND_REPORT_AT_STARTUP", "True")
