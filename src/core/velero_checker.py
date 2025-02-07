import calendar
from datetime import datetime
import json

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess

from utils.handle_error import handle_exceptions_async_method, handle_exceptions_method
from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()
logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))


def flatten_json(obj, level=0, max_level=2):
    """Format JSON with indentation up to max_level, then flatten deeper levels."""
    if isinstance(obj, dict):
        if level >= max_level:
            return json.dumps(obj)  # Flatten deeper levels
        return {k: flatten_json(v, level + 1, max_level) for k, v in obj.items()}
    elif isinstance(obj, list):
        if level >= max_level:
            return json.dumps(obj)  # Flatten deeper levels
        return [flatten_json(v, level + 1, max_level) for v in obj]
    else:
        return obj


class VeleroChecker:
    """
    The class allows to process the data received from k8s APIs
    """

    def __init__(self,
                 queue=None,
                 dispatcher_queue=None,
                 dispatcher_max_msg_len=8000,
                 dispatcher_alive_message_hours=24,
                 k8s_key_config: ConfigK8sProcess = None,
                 daemon=True):

        self.queue = queue
        self.daemon = daemon

        self.dispatcher_max_msg_len = dispatcher_max_msg_len
        self.dispatcher_queue = dispatcher_queue

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.old_data = {}

        self.alive_message_seconds = dispatcher_alive_message_hours * 3600
        self.last_send = calendar.timegm(datetime.today().timetuple())

        self.cluster_name = ""
        self.force_alive_message = False

        # self.send_config = True

        self.final_message = ""
        self.unique_message = False
        self.first_run = (daemon and config_app.send_report_at_startup()) or (daemon is False)

    @staticmethod
    def get_changed_keys(old, new, skip_fields):
        changed = []

        for backup in old:
            if backup in new:
                for key in old[backup]:
                    if key in skip_fields:
                        continue
                    elif old[backup][key] != new[backup][key]:
                        changed.append(backup)
                        break

        return changed

    def __find_dict_difference(self, old_dict, new_dict):
        # Find keys that are unique to each dictionary
        keys_only_in_old_dict = set(old_dict.keys()) - set(new_dict.keys())
        keys_only_in_new_dict = set(new_dict.keys()) - set(old_dict.keys())

        # Check old_dict and new_dict is dict
        if not isinstance(old_dict, dict) or not isinstance(new_dict, dict):
            raise ValueError("old_dict or new_dict is not dict.")

        # Find keys that are common to both dictionaries but have different values
        skip_field = ['expire', 'time_expires']
        changed_keys = self.get_changed_keys(old_dict, new_dict, skip_field)

        # Create dictionaries containing the differing key-value pairs
        old_values = {key: old_dict[key] for key in changed_keys}
        new_values = {key: new_dict[key] for key in changed_keys}

        return {
            "has_diff": len(changed_keys) > 0 or len(list(keys_only_in_old_dict)) > 0 or len(
                list(keys_only_in_new_dict)) > 0,
            "removed": list(keys_only_in_old_dict),
            "added": list(keys_only_in_new_dict),
            "changed": changed_keys,  # list(differing_dict1.keys()),
            "old_values": old_values,
            "new_values": new_values,
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
        # self.print_helper.debug("__put_in_queue__")

        await queue.put(obj)

    @handle_exceptions_async_method
    async def __send_to_dispatcher(self, message):
        """
        Send message to dispatcher engine
        @param message: message to send
        """
        logger.debug(f"send_to_dispatcher. msg len= {len(message)}-unique {self.unique_message} ")
        if len(message) > 0:
            logger.debug(f"{message}")
            # if not self.unique_message or force_message:
            self.last_send = calendar.timegm(datetime.today().timetuple())
            msg = ''
            if 'cluster_name' in message:
                if message['cluster_name'] is not None:
                    msg = 'Cluster: ' + message['cluster_name'] + '\n'
            if 'backups' in message:
                msg += message['backups']
            if 'schedules' in message:
                msg += message['schedules']
            if 'configs' in message:
                msg += message['configs']
            await self.__put_in_queue__(self.dispatcher_queue, msg)

    async def __unpack_data(self, data):
        """
         Check the key received and calls the procedure associated with the key type
        :param data:
        """
        # self.print_helper.debug("__unpack_data")
        try:
            if isinstance(data, dict):
                cluster_name = await self.__process_cluster_name(data)

                schedules: dict[str, str] | None = None
                backups: dict[str, str] | None = None

                if self.first_run:
                    if self.k8s_config.backups_key in data:
                        backups = await self.__process_backups_report(data)
                else:
                    if self.k8s_config.schedules_key in data:
                        schedules = await self.__process_schedule_difference_report(data)
                    if self.k8s_config.backups_key in data:
                        backups = await self.__process_backups_difference_report(data)

                self.old_data = data

                has_diff = False

                messages = dict(cluster_name)
                if isinstance(schedules, dict) and len(schedules) > 0:
                    has_diff = True
                    messages.update(schedules)

                if isinstance(backups, dict) and len(backups) > 0 and backups is not None:
                    has_diff = True
                    messages.update(backups)

                if has_diff or self.first_run:
                    await self.__send_to_dispatcher(messages)

            else:
                logger.error(f"__unpack_data.the message is not a type of dict")

        except Exception as err:
            logger.error(f"__unpack_data {str(err)}")

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
        # logger.info(f"__process_cluster_name__")
        nodes_name = data[self.k8s_config.cluster_name_key]
        # logger.info(f"cluster name {nodes_name}")
        self.cluster_name = {'cluster_name': nodes_name}
        return self.cluster_name

    async def __process_backups_report(self, data):
        # self.print_helper.info("__last_backup_report")
        try:

            backups = data[self.k8s_config.backups_key]
            unscheduled = data[self.k8s_config.unschedule_namespace_key]

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
            backup_failed_validation = 0

            backup_not_retrieved = 0

            # message strings
            message = ''
            message_header = ''
            message_body = ''

            backup_in_progress_str = ''
            backup_failed_str = ''
            backup_partially_failed_str = ''
            error_str = ''
            wrn_str = ''
            backup_expired_str = ''
            backup_failed_validation_str = ''

            # point = '\u2022'
            point = '    •'
            list_point = '        ‣ '

            for backup_name, backup_info in backups.items():
                logger.debug(f'Backup name: {backup_name}')

                if backup_name != "error" or 'schedule' in backup_info:

                    if len(backup_info['expire']) > 0:

                        day = self.__extract_days_from_str(str(backup_info['expire']))
                        if day is None:
                            backup_not_retrieved += 1
                        elif day < self.k8s_config.expires_days_warning:
                            expired_backup += 1
                            backup_expired_str += f'\n{list_point}{str(backup_name)}'

                    # add status field
                    if len(backup_info['phase']) > 0:
                        if backup_info['phase'].lower() == 'completed':
                            backup_completed += 1
                        elif backup_info['phase'].lower() == 'inprogress':
                            backup_in_progress_str += f'\n{list_point}{str(backup_name)}'
                            backup_in_progress += 1
                        elif backup_info['phase'].lower() == 'failedvalidation':
                            backup_failed_validation_str += f'\n{list_point}{str(backup_name)}'
                            backup_failed_validation += 1
                        elif backup_info['phase'].lower() == 'failed':
                            backup_failed_str += f'\n{list_point}{str(backup_name)}'
                            backup_failed += 1
                        elif backup_info['phase'].lower() == 'partiallyfailed':
                            backup_partially_failed_str += f'\n{list_point}{str(backup_name)}'
                            backup_partially_failed += 1

                    # add error field
                    error = self.__get_backup_error_message(str(backup_info['errors']))
                    if len(error) > 0:
                        error_str += f'\n{list_point}{str(backup_name)}'
                        backup_in_errors += 1

                    # add warning field
                    wrn = self.__get_backup_error_message(str(backup_info['warnings']))
                    if len(wrn) > 0:
                        wrn_str += f'\n{list_point}{str(backup_name)}'
                        backup_in_wrn += 1
            # end stats

            message_header += (f'\nNamespaces:'
                               f'\n{point} total={unscheduled["counter_all"]}'
                               f'\n{point} unscheduled={unscheduled["counter"]}'
                               f'\n\nBackups (based on last backup for every schedule and backup without schedule)'
                               f'\n{point} total={backup_count}'
                               f'\n{point} completed={backup_completed}')

            if backup_in_progress > 0:
                message_header += f'\n{point} in progress={backup_in_progress}{backup_in_progress_str}'
            if backup_failed_validation > 0:
                message_body += f'\n{point} failed validation={backup_failed}{backup_failed_validation_str}'
            if backup_in_errors > 0:
                message_body += f'\n{point} with errors={backup_in_errors}{error_str}'
            if backup_in_wrn > 0:
                message_body += f'\n{point} with warnings={backup_in_wrn}{wrn_str}'
            if backup_failed > 0:
                message_body += f'\n{point} failed={backup_failed}{backup_failed_str}'
            if backup_partially_failed > 0:
                message_body += f'\n{point} partially Failed={backup_partially_failed}{backup_partially_failed_str}'
            if expired_backup > 0:
                message_body += (f'\n{point} in warning period={expired_backup} '
                                 f'(expires day less than {self.k8s_config.expires_days_warning}d)'
                                 f'{backup_expired_str}')

            # build unscheduled namespaces string
            if len(unscheduled) > 0:
                str_namespace = ''
                for name_s in unscheduled['difference']:
                    str_namespace += f'{list_point}{name_s}\n'
                if len(str_namespace) > 0:
                    message = (
                        f'\n\nNamespace without active backup ({unscheduled["counter"]}/{unscheduled["counter_all"]})'
                        f':\n{str_namespace}')

            if len(self.old_data) == 0:
                return {'backups': f"{message_header}{message_body}{message}"}
            else:
                return {'backups': message_body}

        except Exception as err:
            logger.error(f"__last_backup_report {str(err)}")

    async def __process_backups_difference_report(self, data):
        logger.info("Check for differences in backups")

        backups = data[self.k8s_config.all_backups_key]

        if self.k8s_config.all_backups_key not in self.old_data or self.old_data[self.k8s_config.all_backups_key] == data[self.k8s_config.all_backups_key]:
            logger.info("Check for differences in backups: do nothing same data")
            return

        backups_diff = self.__find_dict_difference(self.old_data[self.k8s_config.all_backups_key], backups)

        if backups_diff['has_diff']:
            backup_messages = []

            for backup_name in (backups_diff['added'] + backups_diff['changed']):
                backup_info = backups[backup_name]
                message = ''
                if 'phase' not in backup_info or ('phase' in backup_info and len(backup_info['phase']) == 0):
                    logger.error(f'{backup_info["phase"]}: missing phase, maybe waiting for startup')
                elif len(backup_info['phase']) > 0:
                    logger.debug(f'backup_name: {backup_name} Phase: {backup_info["phase"].lower()}')

                    error = self.__get_backup_error_message(str(backup_info['errors']))
                    wrn = self.__get_backup_error_message(str(backup_info['warnings']))

                    if (not config_app.get_notification_skip_completed() or len(error) > 0 or len(wrn) > 0) and \
                            backup_info['phase'].lower() == 'completed':
                        message += (f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} '
                                    f'completed')

                    elif not config_app.get_notification_skip_inprogress() and backup_info['phase'].lower() == 'inprogress':
                        message += (f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} in '
                                    f'progress')

                    elif not config_app.get_notification_skip_deleting() and backup_info['phase'].lower() == 'deleting':
                        message += (f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} '
                                    f'deleting')

                    elif backup_info['phase'].lower() == 'failed':
                        message += (f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} '
                                    f'failed')

                    elif backup_info['phase'].lower() == 'partiallyfailed':
                        message += (f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} '
                                    f'partially failed')

                    elif backup_info['phase'].lower() not in ['completed', 'inprogress', 'deleting', 'failed',
                                                              'partiallyfailed']:
                        message += (f"{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} "
                                    f"{backup_info['phase'].lower()}")

                    # add error field
                    if backup_info['phase'].lower() in ['completed', 'failed', 'partiallyfailed']:
                        if len(error) > 0:
                            message += f' with errors'

                        # add warning field
                        if len(wrn) > 0:
                            message += f' with warnings'

                if message != '':
                    backup_messages.append(message)
            # end for

            if not config_app.get_notification_skip_removed():
                for backup_name in backups_diff['removed']:
                    message = f'{config_app.get_report_backup_item_prefix()}Velero backup {str(backup_name)} removed'
                    backup_messages.append(message)

            if len(backup_messages) > 0:
                return {'backups': '\n'.join(backup_messages[::-1])}
            return None

    async def __process_schedule_difference_report(self, data):
        logger.info("Check for differences in schedules")

        try:
            if self.k8s_config.schedules_key not in self.old_data or self.old_data[self.k8s_config.schedules_key] == data[self.k8s_config.schedules_key]:
                logger.info("Check for differences in schedules: do nothing same data")
                return

            schedule_messages = []
            diff = self.__find_dict_difference(self.old_data[self.k8s_config.schedules_key],
                                               data[self.k8s_config.schedules_key])

            if len(diff) > 0:
                if len(diff['removed']) > 0:
                    for rem in diff['removed']:
                        schedule_messages.append(
                            f'{config_app.get_report_schedule_item_prefix()}Velero scheduled {rem} removed')

                if len(self.old_data[self.k8s_config.schedules_key]) > 0 and len(diff['added']) > 0:
                    for add in diff['added']:
                        schedule_messages.append(
                            f'{config_app.get_report_schedule_item_prefix()}Velero scheduled {add} added')

                if len(diff['old_values']) > 0:
                    for schedule_name in diff['old_values']:
                        message = (f"{config_app.get_report_schedule_item_prefix()}Velero scheduled {schedule_name} "
                                   f"updated:")
                        for field in diff['old_values'][schedule_name]:
                            if diff['old_values'][schedule_name][field] != diff['new_values'][schedule_name][field]:
                                message += (f"\n{field} from {diff['old_values'][schedule_name][field]} "
                                            f"to {diff['new_values'][schedule_name][field]}")
                        schedule_messages.append(message)

            return {'schedules': '\n'.join(schedule_messages[::-1])}

        except Exception as err:
            logger.error(f"{str(err)}")

    @handle_exceptions_async_method
    async def send_active_configuration(self, sub_title=None):
        """
        Send a message to Apprise engine of the active setup
        """
        point = '    •'
        # list_point = '        ‣ '

        title = "velero-watchdog is restarted"
        if sub_title is not None and len(sub_title) > 0:
            title = f"{title}\n{sub_title}"

        logger.info(f"send active configuration")

        msg = f'Configuration setup:\n'
        if self.k8s_config is not None:
            msg = msg + f"{point}Notification backups ENABLE={'TRUE' if self.k8s_config.backup_enable else 'FALSE'}\n"
            msg = msg + f"{point}Notification scheduled ENABLE={'TRUE' if self.k8s_config.schedule_enable else 'FALSE'}\n"
            msg = msg + (f"{point}Notification skip completed="
                         f"{'TRUE' if config_app.get_notification_skip_completed() else 'FALSE'}\n")
            msg = msg + f"{point}Notification skip deleting={'TRUE' if config_app.get_notification_skip_deleting() else 'FALSE'}\n"
            msg = msg + (f"{point}Notification skip in progress="
                         f"{'TRUE' if config_app.get_notification_skip_inprogress() else 'FALSE'}\n")
            msg = msg + f"{point}Notification skip removed={'TRUE' if config_app.get_notification_skip_removed() else 'FALSE'}\n"
            msg = msg + f"{point}Process cycle={config_app.process_run_sec()}\n"
            msg = msg + f"{point}Expire days warning={config_app.velero_expired_days_warning()}\n"
            msg = msg + f"{point}Backups prefix={config_app.get_report_backup_item_prefix()}\n"
            msg = msg + f"{point}Schedules prefix={config_app.get_report_schedule_item_prefix()}\n"

            # if self.alive_message_seconds >= 3600:
            #     msg = msg + f"\nAlive message every {int(self.alive_message_seconds / 3600)} hours"
            # else:
            #     msg = msg + f"\nAlive message every {int(self.alive_message_seconds / 60)} minutes"
        else:
            msg = "Error init config class"

        msg = f"{title}\n\n{msg}"

        await self.__send_to_dispatcher({'cluster_name': config_app.k8s_cluster_identification(), 'configs': msg})

    async def run(self, loop=True):
        """
        Main loop of consumer k8s status_run
        """
        try:
            logger.info("checker run")
            if self.daemon and config_app.send_start_message():  # do not send configuration message in no daemon app
                await self.send_active_configuration()

            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                logger.info("Velero checker: new element received")
                logger.debug(f"Velero checker: new element received"
                             "\n--------------------------------------------------------------------------------------"
                             f"\n{json.dumps(flatten_json(item), sort_keys=True, indent=4)}"
                             f"\n-------------------------------------------------------------------------------------")

                if item is not None:
                    await self.__unpack_data(item)
                    self.first_run = False

        except Exception as err:
            logger.error(f"run {str(err)}")
