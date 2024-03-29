import re
from datetime import datetime
from kubernetes import client, config
from collections import OrderedDict

from config.config import Config

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_method


config_app = Config()

class VeleroStatus:

    @handle_exceptions_method
    def __init__(self, k8s_config):

        self.print_helper = PrintHelper('[core.velero_status]',
                                        level=config_app.get_internal_log_level())

        self.print_helper.debug(f"__init__")

        if k8s_config.k8s_in_cluster_mode:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_file=k8s_config.k8s_config_file)
        self.v1 = client.CoreV1Api()
        self.client = client.CustomObjectsApi()
        self.expires_day_warning = k8s_config.EXPIRES_DAYS_WARNING

        self.ignored_namespace = k8s_config.ignore_namespace

    @handle_exceptions_method
    def _filter_ignored_namespace(self, keys_list, regex_list):
        self.print_helper.debug('_filter_ignored_namespace...')
        # Compile regex patterns from the provided list
        compiled_regex_list = [re.compile(pattern) for pattern in regex_list]

        # Initialize an empty list for the output
        filtered_keys = []
        loop = 0
        # Loop through each key
        for key in keys_list:
            loop += 1
            # Flag to track if the key matches any regex pattern
            match_found = False

            # Check if the key matches any regex pattern
            for pattern in compiled_regex_list:
                if pattern.match(key):
                    match_found = True
                    break

            # If no match is found, add the key to the filtered list
            if not match_found:
                filtered_keys.append(key)
            else:
                self.print_helper.debug(f'_filter_ignored_namespace discard : {key}')

        self.print_helper.debug(f'_filter_ignored_namespace: {loop-len(filtered_keys)}')

        return filtered_keys

    @handle_exceptions_method
    def _get_k8s_namespace(self):
        self.print_helper.debug('_get_namespace_list...')

        # Get namespaces list
        namespace_list = self.v1.list_namespace()

        # Extract namespace list
        namespaces = [namespace.metadata.name for namespace in namespace_list.items]
        all_nm = 0
        ignored_nm = 0
        if len(namespaces) > 0:
            all_nm = len(namespaces)
        self.print_helper.debug(f'_get_namespace_list...=>all:{all_nm}')

        # LS 2023.11.23 add ignored namespace
        if len(self.ignored_namespace) > 0:
            namespaces = self._filter_ignored_namespace(namespaces, self.ignored_namespace)
            ignored_nm = all_nm - len(namespaces)
        self.print_helper.debug(f'_get_namespace_list. all nm {all_nm} Ignored {ignored_nm}')

        self.print_helper.info(f"_get_namespace_list all: {all_nm} "
                               f"after filter: {len(namespaces)} "
                               f"ignored : {ignored_nm}")

        return namespaces

    @handle_exceptions_method
    def _get_k8s_last_backup_status(self, namespace='velero'):

        custom_api = self.client

        # Get schedule from velero namespace
        group = 'velero.io'
        version = 'v1'
        plural = 'backups'
        backup_list = custom_api.list_namespaced_custom_object(group, version, namespace, plural)

        last_backup_info = OrderedDict()

        # Extract last backup for every schedule
        for backup in backup_list.get('items', []):
            if backup.get('metadata', {}).get('labels').get('velero.io/schedule-name'):
                schedule_name = backup['metadata']['labels']['velero.io/schedule-name']
            else:
                schedule_name = None

            # print(f'***\n{backup}\n*****\n')
            # LS 2023.11.26 add namespace
            nm = ''
            if 'namespace' in backup:
                nm = backup['namespace']

            if backup['status'] != {}:
                if 'phase' in backup['status']:
                    phase = backup['status']['phase']
                else:
                    phase = ''
                errors = backup['status'].get('errors', [])
                warnings = backup['status'].get('warnings', [])
                backup_name = backup['metadata']['name']

                time_expires = ''
                if 'phase' in backup['status']:
                    time_expires = backup['status'].get('expiration', "N/A")
                    time_expire__str = str(
                        (datetime.strptime(time_expires, '%Y-%m-%dT%H:%M:%SZ') - datetime.now()).days) + 'd'
                else:
                    if 'progress' in backup['status']:
                        time_expire__str = 'in progress'
                    else:
                        time_expire__str = 'N/A'

                if 'completionTimestamp' in backup['status']:
                    completion_timestamp = backup['status'].get('completionTimestamp')
                else:
                    completion_timestamp = 'N/A'

                backup_same_schedule_name = None
                schedules = []
                backup_same_schedule_data = {}
                if schedule_name is not None:
                    schedules = [last_backup_info[item]["schedule"] for item in dict(last_backup_info)]
                    backup_same_schedule_name = next(
                        (item for item in last_backup_info if last_backup_info[item]["schedule"] == schedule_name),
                        None)
                    if backup_same_schedule_name is not None:
                        backup_same_schedule_data = last_backup_info[backup_same_schedule_name]

                if schedule_name is None \
                        or (schedule_name is not None and schedule_name not in schedules) \
                        or (schedule_name is not None and backup_same_schedule_data is not None and backup_name >
                            backup_same_schedule_data['backup_name']):

                    if backup_same_schedule_name is not None:
                        del last_backup_info[backup_same_schedule_name]
                    last_backup_info[backup_name] = {
                        'backup_name': backup_name,
                        'phase': phase,
                        'namespace': nm,
                        'errors': errors,
                        'warnings': warnings,
                        'time_expires': time_expires,
                        'schedule': schedule_name,
                        'completion_timestamp': completion_timestamp,
                        'expire': time_expire__str
                    }

        return last_backup_info

    @handle_exceptions_method
    def _get_scheduled_namespaces(self):
        all_ns = []
        schedules = self.get_k8s_velero_schedules()
        for schedule in schedules:
            all_ns = all_ns + schedules[schedule]['included_namespaces']
        return all_ns

    @handle_exceptions_method
    def _get_unscheduled_namespaces(self):
        namespaces = self._get_k8s_namespace()
        all_included_namespaces = self._get_scheduled_namespaces()

        difference = list(set(namespaces) - set(all_included_namespaces))
        difference.sort()
        return difference, len(difference), len(namespaces)

    @handle_exceptions_method
    def _get_backup_error_message(self, message):
        if message == '[]':
            return ''
        else:
            return f'{message}'

    @handle_exceptions_method
    def _extract_days_from_str(self, str_number):
        value = -1

        index = str_number.find('d')

        if index != -1:
            value = int(str_number.strip()[:index])

        if value > 0:
            return value
        else:
            return None

    @handle_exceptions_method
    def _extract_resources_from_schedule(self, schedule):
        try:
            schedule_name = schedule['metadata']['name']
            included_namespaces = []
            included_resources = []
            default_volumes_to_fs_backup = []
            cron_time = ''
            if 'spec' in schedule:
                cron_time = schedule['spec']['schedule']
                included_resources = schedule['spec'].get('includedResources', [])
                included_namespaces = schedule['spec']['template'].get('includedNamespaces', [])
                default_volumes_to_fs_backup = schedule['spec']['template'].get('defaultVolumesToFsBackup', [])

            return schedule_name, included_namespaces, included_resources, default_volumes_to_fs_backup, cron_time
        except Exception as e:
            self.print_helper.error(f"run.{e}")

    @handle_exceptions_method
    def get_k8s_velero_schedules(self, namespace='velero'):

        custom_api = self.client

        # Get schedule from velero namespace
        group = 'velero.io'
        version = 'v1'
        plural = 'schedules'
        schedule_list = custom_api.list_namespaced_custom_object(group, version, namespace, plural)

        schedules = {}

        for schedule in schedule_list.get('items', []):
            schedule_name, \
                included_namespaces, \
                included_resources, \
                default_volumes_to_fs_backup, \
                cron_time = self._extract_resources_from_schedule(schedule)
            schedules[schedule_name] = {
                'included_namespaces': included_namespaces,
                'included_resources': included_resources,
                'default_volumes_to_fs_backup': default_volumes_to_fs_backup,
                'cron_time': cron_time
            }
        return schedules

    @handle_exceptions_method
    def get_k8s_last_backup_status(self, namespace='velero'):
        backups = self._get_k8s_last_backup_status(namespace=namespace)
        difference, counter, counter_all = self._get_unscheduled_namespaces()

        unscheduled = {'difference': difference,
                       'counter': counter,
                       'counter_all': counter_all}
        data = {'backups': backups, 'us_ns': unscheduled}

        return data
