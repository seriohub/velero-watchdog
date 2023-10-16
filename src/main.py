from datetime import datetime
from dotenv import load_dotenv
from kubernetes import client, config
import requests
from optparse import OptionParser
from collections import OrderedDict
from utils.print_helper import PrintHelper
from utils.handle_exceptions import *
import json

load_dotenv()


class VeleroWatchdog:

    @handle_exceptions
    def __init__(self):
        self.print_ls = PrintHelper('VeleroWatchdog')  # helper printer class

        # DEBUG
        if os.getenv('DEBUG_ON') is not None:
            self.debug = True if os.getenv('DEBUG_ON').lower() == 'true' else False
        else:
            self.print_ls.wrn('DEBUG_ON missing in .env configuration file, set a default value=FALSE')
            self.debug = False

        # KUBE_CONFIG_FILE
        if os.getenv('KUBE_CONFIG_FILE') is not None:
            self.kube_config_file = os.getenv('KUBE_CONFIG_FILE')
        else:
            self.print_ls.error('KUBE_CONFIG_FILE missing in .env configuration file')
            exit(1)

        # EXPIRES_DAYS_WARNING
        if os.getenv('EXPIRES_DAYS_WARNING') is not None:
            self.expires_day_warning = int(os.getenv('EXPIRES_DAYS_WARNING'))
        else:
            self.print_ls.wrn('EXPIRES_DAYS_WARNING missing in .env configuration file, set a default value=29days')
            self.expires_day_warning = 29

        self.accepted_command = ['get-ns',
                                 'get-schedule',
                                 'get-unschedule-ns',
                                 'get-backups-status',
                                 'report-std',
                                 'report-std-sum',
                                 'report-tgm',
                                 'report-tgm-sum',
                                 'exit'
                                 ]

        if os.getenv('ENABLE_TELEGRAM_NOTIFICATION') is not None:
            self.enable_telegram_notification = True if os.getenv('ENABLE_TELEGRAM_NOTIFICATION').lower() == 'true' else False
        else:
            self.enable_telegram_notification = False

        if self.enable_telegram_notification:
            if os.getenv('TELEGRAM_API_TOKEN') is not None:
                self.telegram_api_token = os.getenv('TELEGRAM_API_TOKEN')
            else:
                self.print_ls.error('TELEGRAM_API_TOKEN missing in .env configuration file')
                exit(2)
            if os.getenv('TELEGRAM_CHAT_ID') is not None:
                self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
            else:
                self.print_ls.error('TELEGRAM_CHAT_ID missing in .env configuration file')
                exit(3)

        self.print_ls.debug_if(self.debug, f'Validation: {self.expires_day_warning} - Debug: {self.debug}')

    @handle_exceptions
    def _get_k8s_namespace(self):
        self.print_ls.debug_if(self.debug, '_get_namespace_list...')

        # Load cluster configuration
        config.load_kube_config(config_file=self.kube_config_file)

        # Create API object
        v1 = client.CoreV1Api()

        # Get namespaces list
        namespace_list = v1.list_namespace()

        # Extract namespace list
        namespaces = [namespace.metadata.name for namespace in namespace_list.items]

        return namespaces

    @handle_exceptions
    def _get_k8s_velero_schedules(self, namespace='velero'):
        self.print_ls.debug_if(self.debug, f'_get_velero_schedules: {namespace}...')

        # Load cluster configuration
        config.load_kube_config(config_file=self.kube_config_file)

        # Create API object
        custom_api = client.CustomObjectsApi()

        # Get schedule from velero namespace
        group = 'velero.io'
        version = 'v1'
        plural = 'schedules'
        schedule_list = custom_api.list_namespaced_custom_object(group, version, namespace, plural)

        return schedule_list.get('items', [])

    @handle_exceptions
    def _get_k8s_last_backup_status(self, namespace='velero'):
        self.print_ls.debug_if(self.debug, 'get_last_backup_info')

        # Load cluster configuration
        config.load_kube_config(config_file=self.kube_config_file)

        # Create API object
        custom_api = client.CustomObjectsApi()

        # Get schedule from velero namespace
        group = 'velero.io'
        version = 'v1'
        plural = 'backups'
        backup_list = custom_api.list_namespaced_custom_object(group, version, namespace, plural)

        # last_backup_info = {}
        last_backup_info = OrderedDict()

        # Extract last backup for every schedule
        for backup in backup_list.get('items', []):
            schedule_name = backup['metadata']['labels']['velero.io/schedule-name']

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

                if schedule_name not in last_backup_info or backup_name > last_backup_info[schedule_name]['backup_name']:
                    last_backup_info[schedule_name] = {
                        'backup_name': backup_name,
                        'phase': phase,
                        'errors': errors,
                        'warnings': warnings,
                        'time_expires': time_expires,
                        'schedule': schedule_name,
                        'completion_timestamp': completion_timestamp,
                        'expire': time_expire__str
                    }
        return last_backup_info

    @handle_exceptions
    def _get_scheduled_namespaces(self):
        self.print_ls.debug_if(self.debug, '_get_all_included_namespaces...')
        all_ns = []
        schedules = veleroWatchdog._get_k8s_velero_schedules()
        for schedule in schedules:
            _, included_namespaces, _, _, _ = veleroWatchdog._extract_resources_from_schedule(schedule)
            all_ns = all_ns + included_namespaces
        return all_ns

    @handle_exceptions
    def _get_unscheduled_namespaces(self):
        self.print_ls.debug_if(self.debug, '__get_ns_no_schedule...')
        namespaces = self._get_k8s_namespace()
        all_included_namespaces = self._get_scheduled_namespaces()

        difference = list(set(namespaces) - set(all_included_namespaces))
        difference.sort()
        return difference, len(difference), len(namespaces)

    @handle_exceptions
    def _get_backup_error_message(self, message):
        self.print_ls.debug_if(self.debug, '_get_backup_error_message...')
        if message == '[]':
            return ''
        else:
            return f'{message}'

    @handle_exceptions
    def _extract_days_from_str(self, str_number):
        self.print_ls.debug_if(self.debug, f'__get_number_from_str: {str_number}')
        value = -1

        index = str_number.find('d')

        if index != -1:
            value = int(str_number.strip()[:index])

        if value > 0:
            return value
        else:
            return None

    @handle_exceptions
    def _extract_resources_from_schedule(self, schedule):
        self.print_ls.debug_if(self.debug, f'_extract_resources_from_schedule {schedule["metadata"]["name"]}...')
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

    @handle_exceptions
    def _send_to_telegram(self, message):

        api_url = f'https://api.telegram.org/bot{self.telegram_api_token}/sendMessage'

        try:
            response = requests.post(api_url, json={'chat_id': self.telegram_chat_id, 'text': message})
            status = json.loads(response.text)['ok'] is True
            if status:
                self.print_ls.info(f'Sending telegram notification done')
            else:
                self.print_ls.wrn(f'Sending telegram notification failed')
        except Exception as e:
            print(e)

    @handle_exceptions
    def print_namespaces(self):
        self.print_ls.debug_if(self.debug, 'print_namespaces_list...')
        namespaces = veleroWatchdog._get_k8s_namespace()
        print('Namespaces list:')
        for namespace in namespaces:
            print('\t', namespace)

    @handle_exceptions
    def print_velero_schedules(self):
        self.print_ls.debug_if(self.debug, 'print_velero_schedules...')

        schedules = veleroWatchdog._get_k8s_velero_schedules()
        print('Velero Schedules:')

        print('{:<40} {:<15} {:<40} {:<40} {:<20}'.format('Schedule name',
                                                          'Cron',
                                                          'Included Namespaces',
                                                          'Included Resources',
                                                          'Included All Volume'))

        for schedule in schedules:
            schedule_name, \
                included_namespaces, \
                included_resources, \
                default_volumes_to_fs_backup, \
                cron_time = veleroWatchdog._extract_resources_from_schedule(schedule)

            print('{:<40} {:<15} {:<40} {:<40} {:<20}'.format(str(schedule_name),
                                                              str(cron_time),
                                                              str(included_namespaces),
                                                              str(included_namespaces),
                                                              str(default_volumes_to_fs_backup)
                                                              )
                  )

    @handle_exceptions
    def print_unscheduled_namespaces(self):
        self.print_ls.debug_if(self.debug, 'print_unscheduled_namespaces...')
        difference, counter, counter_all = self._get_unscheduled_namespaces()
        print(f'Namespace without scheduled backup [{counter}/{counter_all}]')
        print(difference)

    @handle_exceptions
    def print_report(self, only_summary_report=False, send_to_telegram=True, send_to_stdout=False):
        self.print_ls.debug_if(self.debug, 'print_report...')

        point = '\u2022'

        # unscheduled namespaces
        difference, counter, counter_all = self._get_unscheduled_namespaces()

        # backup status info
        backups = self._get_k8s_last_backup_status()

        # output message
        message = ''

        # counter
        backup_count = len(backups)
        backup_completed = 0
        backup_in_progress = 0
        backup_in_errors = 0
        backup_in_wrn = 0
        expired_backup = 0
        backup_not_retrieved = 0

        # message strings
        backup_in_progress_str = ''
        error_str = ''
        wrn_str = ''

        for schedule_name, backup_info in backups.items():
            self.print_ls.debug_if(self.debug, f'Backup schedule: {schedule_name}')

            #
            # build current state string
            #
            current_state = str(schedule_name) + '\n'

            # add end at field
            if len(backup_info['completion_timestamp']) > 0:
                current_state += '\t\t end at=' + str(backup_info['completion_timestamp']) + '\n'

            # add expire field
            if len(backup_info['expire']) > 0:
                current_state += '\t\t expire=' + str(backup_info['expire'])

                day = self._extract_days_from_str(str(backup_info['expire']))
                if day is None:
                    backup_not_retrieved += 1
                    current_state += f'**IS NOT VALID{backup_info["expire"]}'
                elif day < self.expires_day_warning:
                    expired_backup += 1
                    current_state += '**WARNING'

                current_state += '\n'

            # add status field
            if len(backup_info['phase']) > 0:
                current_state += '\t\t status=' + str(backup_info['phase']) + '\n'
                if backup_info['phase'].lower() == 'completed':
                    backup_completed += 1
                elif backup_info['phase'].lower() == 'inprogress':
                    backup_in_progress_str += f'\t\t{str(schedule_name)}\n'
                    backup_in_progress += 1

            # add error field
            error = self._get_backup_error_message(str(backup_info['errors']))
            if len(error) > 0:
                error_str += f'\t\t{str(schedule_name)}'
                current_state += '\t\t' + 'error=' + error + ' '
                backup_in_errors += 1

            # add warning field
            wrn = self._get_backup_error_message(str(backup_info['warnings']))
            if len(wrn) > 0:
                wrn_str += f'\t\t{str(schedule_name)}'
                current_state += '\t\t' + 'warning=' + wrn + ' '
                backup_in_wrn += 1

            current_state += '\n'
            message += current_state

        message = f'Backup details [{backup_count}/{counter_all}]:\n{message}'

        message_header = ((f'{point} Namespaces={counter_all} \n'
                           f'{point} Unscheduled namespaces={counter}\n'
                           f'{point} Backup active={backup_count} ') +
                          f'\n{point} Completed={backup_completed}')

        if backup_in_progress > 0:
            message_header += f'\n{point} In Progress={backup_in_progress}\n{backup_in_progress_str}'
        if backup_in_errors > 0:
            message_header += f'\n{point} Errors={backup_in_errors}\n{error_str}'
        if backup_in_wrn > 0:
            message_header += f'\n{point} Wrn={backup_in_wrn}\n{wrn_str}'

        if expired_backup > 0:
            message_header += f'\nNumber of backups in warning period={expired_backup} [expires day less than {self.expires_day_warning}d]'

        if send_to_stdout:
            print(f'{message_header}')

        if send_to_telegram is True:
            self._send_to_telegram(message_header)

        if not only_summary_report and send_to_stdout:
            print(f'{message}')

        if not only_summary_report and send_to_telegram:
            self._send_to_telegram(message)

        if len(difference) > 0:
            str_namespace = ''
            for name_s in difference: 
                str_namespace += f'\t{name_s}\n'
            if len(str_namespace) > 0:
                message = f'Namespace without active backup [{counter}/{counter_all}]:\n{str_namespace}'
                if not only_summary_report:
                    print(f'{message}')

        if not only_summary_report and send_to_telegram:
            self._send_to_telegram(message)

    @handle_exceptions
    def print_last_backup_status(self):
        self.print_ls.debug_if(self.debug, 'print_last_backup_status...')

        backup_info_dict = self._get_k8s_last_backup_status()
        print('Details last backup operations:')
        print('{:<40} {:<60} {:<25} {:<25} {:<10} {:<20} {:<20} {:<20} '.format('Schedula',
                                                                                'Name',
                                                                                'Completion Timestamp',
                                                                                'Expiration',
                                                                                'Expires',
                                                                                'Phase',
                                                                                'Errors',
                                                                                'Warning',
                                                                                )
              )

        for schedule_name, backup_info in backup_info_dict.items():
            # for backup_info in backup_info_list:
            print('{:<40} {:<60} {:<25} {:<25} {:<10} {:<20} {:<20} {:<20}'.format(str(backup_info['schedule']),
                                                                                   str(backup_info['backup_name']),
                                                                                   str(backup_info['completion_timestamp']),
                                                                                   str(backup_info['time_expires']),
                                                                                   str(backup_info['expire']),
                                                                                   str(backup_info['phase']),
                                                                                   str(backup_info['errors']),
                                                                                   str(backup_info['warnings'])
                                                                                   )
                  )

    @handle_exceptions
    def print_synopsis(self):
        highlight = '\033[1m'
        end = '\033[0m'
        print('---')
        print('Usage:\n\t' + highlight + 'python3 main.py [command]' + end)
        print('Commands available:')

        print('\t' + highlight + 'get-ns' + end + '\t\t\tnamespaces list')
        print('\t' + highlight + 'get-schedule' + end + '\t\tschedule list')
        print('\t' + highlight + 'get-unschedule-ns' + end + '\tunschedule namespace list')
        print('\t' + highlight + 'get-backups-status' + end + '\tbackup status')

        print('\t' + highlight + 'report-std' + end + '\t\tbackups status on standard output')
        print('\t' + highlight + 'report-std-sum' + end + '\t\tsummary backups status to standard output')
        if self.enable_telegram_notification:
            print('\t' + highlight + 'report-tgm' + end + '\t\treport to telegram')
            print('\t' + highlight + 'report-tgm-sum' + end + '\t\tsummary report to telegram')
        print('\t' + highlight + 'exit' + end)
        print('---')

    @handle_exceptions
    def _match_command(self, command):
        if command == 'get-ns':
            self.print_namespaces()
        elif command == 'get-schedule':
            self.print_velero_schedules()
        elif command == 'get-unschedule-ns':
            self.print_unscheduled_namespaces()
        elif command == 'get-backups-status':
            self.print_last_backup_status()
        elif command == 'report-std':
            self.print_report(only_summary_report=False,
                              send_to_telegram=False,
                              send_to_stdout=True)
        elif command == 'report-std-sum':
            self.print_report(only_summary_report=True,
                              send_to_telegram=False,
                              send_to_stdout=True)
        elif self.enable_telegram_notification and command == 'report-tgm':
            self.print_report(only_summary_report=False,
                              send_to_telegram=True,
                              send_to_stdout=False)
        elif self.enable_telegram_notification and command == 'report-tgm-sum':
            self.print_report(only_summary_report=True,
                              send_to_telegram=True,
                              send_to_stdout=False)

    @handle_exceptions
    def run(self, command):
        self.print_ls.debug_if(self.debug, 'run')

        if command is not None and len(command) > 0:
            if command not in self.accepted_command:
                print('WARNING: \033[1m' + command + '\033[0m' + ' not recognized')
                self.print_synopsis()
            else:
                self._match_command(command)
            exit(0)

        exit_command = False
        while exit_command is False:
            self.print_synopsis()

            command = input('>>')
            if command not in self.accepted_command:
                print('WARNING: \033[1m' + command + '\033[0m' + ' not recognized')
                self.print_synopsis()
            else:
                self._match_command(command)
                if command == 'exit':
                    exit_command = True


if __name__ == '__main__':
    inline_command = None
    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage)
    parser.add_option('-v',
                      '--verbose',
                      help='increase output verbosity',
                      action='store_true',
                      default=False)
    (options, args) = parser.parse_args()
    if options.verbose:
        print(f'args:{args}')
        print(f'options:{options}')
        print('Starting program with verbosity')

    if args is not None:
        if len(args) > 0:
            inline_command = args[0]
    if options.verbose:
        print(f'Command inline: {inline_command}')

    veleroWatchdog = VeleroWatchdog()
    veleroWatchdog.run(inline_command)
