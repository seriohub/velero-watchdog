import calendar
from datetime import datetime

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_async_method, handle_exceptions_method


config_app = Config()


class VeleroChecker:
    """
    The class allows to process the data received from k8s APIs
    """

    def __init__(self,
                 queue=None,
                 dispatcher_queue=None,
                 dispatcher_max_msg_len=8000,
                 dispatcher_alive_message_hours=24,
                 k8s_key_config: ConfigK8sProcess = None):

        self.print_helper = PrintHelper('[core.velero_checker]',
                                        level=config_app.get_internal_log_level())

        self.queue = queue

        self.dispatcher_max_msg_len = dispatcher_max_msg_len
        self.dispatcher_queue = dispatcher_queue

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.old_schedule_status = {}
        self.old_backup = {}

        self.alive_message_seconds = dispatcher_alive_message_hours * 3600
        self.last_send = calendar.timegm(datetime.today().timetuple())

        self.cluster_name = ""
        self.force_alive_message = False

        self.send_config = False

        self.final_message = ""
        self.unique_message = False
        self.first_run = True

    @staticmethod
    def __find_dict_difference(dict1, dict2):
        # Find keys that are unique to each dictionary
        keys_only_in_dict1 = set(dict1.keys()) - set(dict2.keys())
        keys_only_in_dict2 = set(dict2.keys()) - set(dict1.keys())

        # Find keys that are common to both dictionaries but have different values
        differing_keys = [key for key in dict1 if key in dict2 and dict1[key] != dict2[key]]

        # Create dictionaries containing the differing key-value pairs
        differing_dict1 = {key: dict1[key] for key in differing_keys}
        differing_dict2 = {key: dict2[key] for key in differing_keys}

        return {
            "removed": list(keys_only_in_dict1),
            "added": list(keys_only_in_dict2),
            "changed": list(differing_dict1.keys()),
            "old_values": differing_dict1,
            "new_values": differing_dict2,
        }

    @handle_exceptions_async_method
    async def __put_in_queue__(self,
                               queue,
                               obj):
        """
        Add new element to the queue
        :param queue: reference to a queue
        :param obj: objet to add
        """
        self.print_helper.debug("__put_in_queue__")

        await queue.put(obj)

    @handle_exceptions_async_method
    async def __send_to_dispatcher(self, message):
        """
        Send message to dispatcher engine
        @param message: message to send
        """
        self.print_helper.info(f"send_to_dispatcher. msg len= {len(message)}-unique {self.unique_message} ")
        if len(message) > 0:
            self.print_helper.debug(message)
            # if not self.unique_message or force_message:
            self.last_send = calendar.timegm(datetime.today().timetuple())
            msg = ''
            if 'cluster_name' in message:
                if message['cluster_name'] is not None:
                    msg += 'Cluster: ' + message['cluster_name'] + '\n'
            if 'backups' in message:
                msg += message['backups']
            if 'schedules' in message:
                msg += message['schedules']
            await self.__put_in_queue__(self.dispatcher_queue, msg)

    async def __unpack_data(self, data):
        """
         Check the key received and calls the procedure associated with the key type
        :param data:
        """
        self.print_helper.debug("__unpack_data")
        try:
            if isinstance(data, dict):

                cluster_name = await self.__process_cluster_name(data)

                schedules = await self.__process_schedule_report(data[self.k8s_config.schedule_key])

                if self.first_run:
                    backups = await self.__process_backups_report(data[self.k8s_config.backup_key])
                else:
                    # backups = await self.__process_difference_report(data[self.k8s_config.backup_key])
                    backups = await self.__process_backups_difference_report(data['all_backups'])

                # self.old_backup = data[self.k8s_config.backup_key]
                self.old_backup = data['all_backups']

                messages = dict(cluster_name)
                has_diff = False
                if isinstance(schedules, dict) and len(schedules) > 0:
                    has_diff = True
                    messages.update(schedules)
                if self.first_run or (isinstance(backups, dict) and len(backups) > 0):
                    has_diff = True
                    messages.update(backups)

                if has_diff:
                    await self.__send_to_dispatcher(messages)

            else:
                self.print_helper.info(f"__unpack_data.the message is not a type of dict")

        except Exception as err:
            self.print_helper.error_and_exception(f"__unpack_data", err)

    @handle_exceptions_method
    def __get_backup_error_message(self, message):
        # self.print_helper.info("_get_backup_error_message")
        if message == '[]':
            return ''
        else:
            return f'{message}'

    @handle_exceptions_method
    def __extract_days_from_str(self, str_number):
        # self.print_helper.info("_extract_days_from_str")
        value = -1

        index = str_number.find('d')

        if index != -1:
            value = int(str_number.strip()[:index])

        if value > 0:
            return value
        else:
            return None

    async def __process_cluster_name(self, data):
        """
        Obtain cluster name
        @param data:
        """
        self.print_helper.info(f"__process_cluster_name__")
        nodes_name = data[self.k8s_config.cluster_name_key]
        self.print_helper.info(f"cluster name {nodes_name}")
        self.cluster_name = {'cluster_name': nodes_name}
        return self.cluster_name

    async def __process_backups_report(self, data):
        self.print_helper.info("__last_backup_report")
        try:

            backups = data['backups']
            unscheduled = data['us_ns']

            if self.old_backup == data:
                self.print_helper.info("__last_backup_report. do nothing same data")
                return

            old_backups = {}
            old_unscheduled = {}

            if len(self.old_backup) > 0:
                old_backups = self.old_backup['backups']
                old_unscheduled = self.old_backup['us_ns']

            # print difference in stdout
            if backups != old_backups:
                self.print_helper.info("__last_backup_report. backup status changed")
                # print difference
                if len(old_backups) > 0:
                    diff = self.__find_dict_difference(old_backups, backups)
                    self.print_helper.info(f'Difference in backups : {diff}')
                else:
                    self.print_helper.info("__last_backup_report. backup status changed. no old value set")

            if unscheduled != old_unscheduled:
                self.print_helper.info("__last_backup_report. unscheduled namespaces status changed")
                if len(old_unscheduled) > 0:
                    diff = self.__find_dict_difference(old_unscheduled, unscheduled)
                    self.print_helper.info(f'Difference in schedules : {diff}')
                else:
                    self.print_helper.info("__last_backup_report. unscheduled status changed. no old value set")

            # build message for dispatch

            # counter
            backup_count = len(backups)
            backup_completed = 0
            backup_in_progress = 0
            backup_failed = 0
            backup_partially_failed = 0
            backup_in_errors = 0
            backup_in_wrn = 0
            expired_backup = 0
            backup_not_retrieved = 0

            # message strings
            message = ''
            message_header = ''
            message_body = ''
            backup_in_progress_str = ''
            error_str = ''
            wrn_str = ''
            backup_failed_str = ''
            backup_partially_failed_str = ''
            backup_expired_str = ''

            # point = '\u2022'
            point = '-'

            for backup_name, backup_info in backups.items():
                self.print_helper.debug(f'Backup schedule: {backup_name}')

                if backup_name != "error" or 'schedule' in backup_info:

                    if len(backup_info['expire']) > 0:

                        day = self.__extract_days_from_str(str(backup_info['expire']))
                        if day is None:
                            backup_not_retrieved += 1
                        elif day < self.k8s_config.EXPIRES_DAYS_WARNING:
                            expired_backup += 1
                            backup_expired_str += f'\n\t    - {str(backup_name)}'

                    # add status field
                    if len(backup_info['phase']) > 0:
                        if backup_info['phase'].lower() == 'completed':
                            backup_completed += 1
                        elif backup_info['phase'].lower() == 'inprogress':
                            backup_in_progress_str += f'\n    - {str(backup_name)}'
                            backup_in_progress += 1
                        elif backup_info['phase'].lower() == 'failed':
                            backup_failed_str += f'\n    - {str(backup_name)}'
                            backup_failed += 1
                        elif backup_info['phase'].lower() == 'partiallyfailed':
                            backup_partially_failed_str += f'\n    - {str(backup_name)}'
                            backup_partially_failed += 1

                    # add error field
                    error = self.__get_backup_error_message(str(backup_info['errors']))
                    if len(error) > 0:
                        error_str += f'\t- {str(backup_name)}'
                        backup_in_errors += 1

                    # add warning field
                    wrn = self.__get_backup_error_message(str(backup_info['warnings']))
                    if len(wrn) > 0:
                        wrn_str += f'\t- {str(backup_name)}'
                        backup_in_wrn += 1
            # end stats

            message_header += (f'\nNamespaces:'
                               f'\n{point} total={unscheduled["counter_all"]}'
                               f'\n{point} unscheduled={unscheduled["counter"]}'
                               f'\n\nBackups (based on last backup for every schedule and backup without schedule)'
                               f'\n{point} total={backup_count}'
                               f'\n{point} completed={backup_completed}')

            if backup_in_progress > 0:
                message_header += f'\n{point} in Progress={backup_in_progress}\n{backup_in_progress_str}'
            if backup_in_errors > 0:
                message_body += f'\n{point} with Errors={backup_in_errors}\n{error_str}'
            if backup_in_wrn > 0:
                message_body += f'\n{point} with Warnings={backup_in_wrn}\n{wrn_str}'
            if backup_failed > 0:
                message_body += f'\n{point} failed={backup_failed}{backup_failed_str}'
            if backup_partially_failed > 0:
                message_body += f'\n{point} partially Failed={backup_partially_failed}{backup_partially_failed_str}'
            if expired_backup > 0:
                message_body += (f'\n{point} in warning period={expired_backup} '
                                 f'[expires day less than {self.k8s_config.EXPIRES_DAYS_WARNING}d]'
                                 f'{backup_expired_str}')

            # build unscheduled namespaces string
            if len(unscheduled) > 0:
                str_namespace = ''
                for name_s in unscheduled['difference']:
                    str_namespace += f'\t    - {name_s}\n'
                if len(str_namespace) > 0:
                    message = (
                        f'\n\nNamespace without active backup [{unscheduled["counter"]}/{unscheduled["counter_all"]}]'
                        f':\n{str_namespace}')

            if len(self.old_backup) == 0:
                return {'backups':  f"{message_header}{message_body}{message}"}
            else:
                return {'backups':  message_body}

        except Exception as err:
            self.print_helper.error_and_exception(f"__last_backup_report", err)

    async def __process_backups_difference_report(self, data):
        self.print_helper.info("__process_difference_report")

        backups = data['backups']

        if self.old_backup == data:
            self.print_helper.info("__process_difference_report. do nothing same data")
            return

        old_backups = {}

        if len(self.old_backup) > 0:
            old_backups = self.old_backup['backups']

        backups_diff = self.__find_dict_difference(old_backups, backups)

        backup_completed = 0
        backup_in_progress = 0
        backup_failed = 0
        backup_partially_failed = 0
        backup_in_errors = 0
        backup_in_wrn = 0
        backup_removed = 0

        message_body = ''
        backup_in_progress_str = ''
        error_str = ''
        wrn_str = ''
        backup_failed_str = ''
        backup_partially_failed_str = ''
        backup_completed_str = ''
        backup_removed_str = ''

        # point = '\u2022'
        point = '-'

        for backup_name in (backups_diff['added'] + backups_diff['changed']):
            backup_info = backups[backup_name]
            if len(backup_info['phase']) == 0:
                self.print_helper.error(len(backup_info['phase']))
                self.print_helper.error(backup_info['phase'])
            if len(backup_info['phase']) > 0:
                if not config_app.get_notification_skip_completed() and backup_info['phase'].lower() == 'completed':
                    backup_completed += 1
                    backup_completed_str += f'\n\tVelero backup {str(backup_name)} completed'

                elif not config_app.get_notification_skip_inprogress() and backup_info['phase'].lower() == 'inprogress':
                    backup_in_progress_str += f'\n\tVelero backup {str(backup_name)} in progress'
                    backup_in_progress += 1

                elif backup_info['phase'].lower() == 'failed':
                    backup_failed_str += f'\n\tVelero backup {str(backup_name)} failed'
                    backup_failed += 1

                elif backup_info['phase'].lower() == 'partiallyfailed':
                    backup_partially_failed_str += f'\n\tVelero backup {str(backup_name)} partially failed'
                    backup_partially_failed += 1

                else:
                    backup_in_progress_str += f"\n\tVelero backup {str(backup_name)} {backup_info['phase'].lower()}"
                    backup_in_progress += 1

                # add error field
                error = self.__get_backup_error_message(str(backup_info['errors']))
                if len(error) > 0:
                    error_str += f'\tVelero backup {str(backup_name)} has errors'
                    backup_in_errors += 1

                # add warning field
                wrn = self.__get_backup_error_message(str(backup_info['warnings']))
                if len(wrn) > 0:
                    wrn_str += f'\tVelero backup {str(backup_name)} has warnings'
                    backup_in_wrn += 1

        if not config_app.get_notification_skip_removed():
            for backup_name in backups_diff['removed']:
                backup_removed += 1
                backup_removed_str += f'\n\tVelero backup {str(backup_name)} removed'

        # end stats
        if backup_completed > 0:
            message_body += f'\n{point} Backups completed={backup_completed}{backup_completed_str}'
        if backup_removed > 0:
            message_body += f'\n{point} Backups removed§={backup_removed}{backup_removed_str}'
        if backup_in_progress > 0:
            message_body += f'\n{point} Backups in progress={backup_in_progress}{backup_in_progress_str}'
        if backup_in_errors > 0:
            message_body += f'\n{point} Backups with errors={backup_in_errors}\n{error_str}'
        if backup_in_wrn > 0:
            message_body += f'\n{point} Backups with warnings={backup_in_wrn}\n{wrn_str}'
        if backup_failed > 0:
            message_body += f'\n{point} Backups failed={backup_failed}{backup_failed_str}'
        if backup_partially_failed > 0:
            message_body += f'\n{point} Backups partially failed={backup_partially_failed}{backup_partially_failed_str}'

        return {'backups': message_body}

    async def __process_schedule_report(self, data):
        self.print_helper.info("__process_schedule_report")

        try:
            if self.old_schedule_status == data:
                self.print_helper.info("__process_schedule_report. do nothing same data")
                return
            message = ''
            diff = self.__find_dict_difference(self.old_schedule_status, data)

            if len(diff) > 0:
                if len(diff['removed']) > 0:
                    for rem in diff['removed']:
                        message += f"\nVelero scheduled {rem} removed"

                if len(self.old_schedule_status) > 0 and len(diff['added']) > 0:
                    for add in diff['added']:
                        message += f"\nVelero scheduled {add} added"

                if len(diff['old_values']) > 0:
                    for schedule_name in diff['old_values']:
                        message += f"\nVelero scheduled {schedule_name} updated:"
                        for field in diff['old_values'][schedule_name]:
                            if diff['old_values'][schedule_name][field] != diff['new_values'][schedule_name][field]:
                                message += (f"\n{field} from {diff['old_values'][schedule_name][field]} "
                                            f"to {diff['new_values'][schedule_name][field]}")

            self.old_schedule_status = data

            return {'schedules': message}

        except Exception as err:
            self.print_helper.error_and_exception(f"__process_schedule_report", err)

    @handle_exceptions_async_method
    async def send_active_configuration(self, sub_title=None):
        """
        Send a message to Telegram engine of the active setup
        """
        title = "velero-watchdog is restarted"
        if sub_title is not None and len(sub_title) > 0:
            title = f"{title}\n{sub_title}"

        self.print_helper.info(f"send_active_configuration")

        msg = f'Configuration setup:\n'
        if self.k8s_config is not None:
            msg = msg + f"  . backup status= {'ENABLE' if self.k8s_config.backup_enable else '.'}\n"
            msg = msg + f"  . scheduled status= {'ENABLE' if self.k8s_config.schedule_enable else '.'}\n"

            if self.alive_message_seconds >= 3600:
                msg = msg + f"\nAlive message every {int(self.alive_message_seconds / 3600)} hours"
            else:
                msg = msg + f"\nAlive message every {int(self.alive_message_seconds / 60)} minutes"
        else:
            msg = "Error init config class"

        msg = f"{title}\n\n{msg}"
        await self.__send_to_dispatcher(msg)

    async def run(self, loop=True):
        """
        Main loop of consumer k8s status_run
        """
        try:
            self.print_helper.info("checker run")
            if self.send_config:
                await self.send_active_configuration()

            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                self.print_helper.info(f"checker new element received")

                if item is not None:
                    await self.__unpack_data(item)
                    self.first_run = False

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
