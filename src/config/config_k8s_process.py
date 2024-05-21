from config.config import Config


class ConfigK8sProcess:
    def __init__(self, cl_config: Config = None):
        self.k8s_in_cluster_mode = True
        self.k8s_config_file = None

        self.cluster_name = None
        self.cluster_name_key = 'cluster'

        self.backup_enable = True
        self.backups_key = 'last_backups'  # last and one time backups
        self.all_backups_key = 'backups'

        self.unschedule_namespace_key = 'un_ns'

        self.schedule_enable = True
        self.schedules_key = 'schedules'

        self.disp_msg_key_unique = True  # Fixed True
        self.disp_msg_key_start = 'msg_key_start'
        self.disp_msg_key_end = 'msg_key_end'

        # LS 2023.11.23 add ignored namespaces
        self.ignore_namespace = []

        if cl_config is not None:
            self.__init_configuration_app__(cl_config)

    def __print_configuration__(self):
        """
        Print setup class
        """
        print(f"INFO    [Process setup] k8s cluster name= {self.cluster_name}")

        print(f"INFO    [Process setup] k8s in cluster mode={self.k8s_in_cluster_mode}")
        print(f"INFO    [Process setup] k8s config file={self.k8s_config_file}")
        print(f"INFO    [Process setup] velero backup enable={self.backup_enable}")
        print(f"INFO    [Process setup] velero schedule enable={self.schedule_enable}")
        print(f"INFO    [Process setup] k8s send summary message={self.disp_msg_key_unique}")

        print(f"INFO    [Process setup] k8s ignored namespaces: regex defined {len(self.ignore_namespace)}")

    def __init_configuration_app__(self, cl_config: Config):
        """
        Init configuration class reading .env file
        """
        self.backup_enable = cl_config.velero_backup_enable()
        self.schedule_enable = cl_config.velero_schedule_enable()
        self.EXPIRES_DAYS_WARNING = cl_config.velero_expired_days_warning()
        self.cluster_name = cl_config.k8s_cluster_identification()
        self.k8s_in_cluster_mode = cl_config.k8s_incluster_mode()
        self.k8s_config_file = cl_config.k8s_config_file()

        # LS 2023.11.23 add ignored namespace
        self.ignore_namespace = cl_config.get_regex_patterns_ignore_nm()

        self.__print_configuration__()
