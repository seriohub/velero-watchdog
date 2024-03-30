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
            # if not self.unique_message or force_message:
            self.last_send = calendar.timegm(datetime.today().timetuple())
            msg = ''
            if 'cluster_name' in message:
                msg += message['cluster_name'] + '\n'
            if 'backups' in message:
                msg += message['backups']
            if 'schedules' in message:
                msg += message['schedules']
            await self.__put_in_queue__(self.dispatcher_queue, msg)
            # else:
            #
            #     if len(self.final_message) > 0:
            #         self.print_helper.info(f"send_to_dispatcher. concat message- len({len(self.final_message)})")
            #         self.final_message = f"{self.final_message}\n{'-' * 20}\n{message}"
            #     else:
            #         self.print_helper.info(f"send_to_dispatcher. start message")
            #         self.final_message = f"{message}"

    # @handle_exceptions_async_method
    # async def send_to_dispatcher_summary(self):
    #     """
    #     Send summary message to dispatcher engine
    #     """
    #
    #     self.print_helper.info(f"send_to_dispatcher_summary. message-len= {len(self.final_message)}")
    #     # Chck if the final message is not empty
    #     if len(self.final_message) > 10:
    #         # LS 2023.11.09 add cluster name
    #         self.final_message = f"Cluster name: {self.cluster_name}\nStart report\n{self.final_message}\nEnd report"
    #         self.last_send = calendar.timegm(datetime.today().timetuple())
    #         await self.__put_in_queue__(self.dispatcher_queue,
    #                                     self.final_message)
    #
    #     self.final_message = ""
    #     self.unique_message = False

    async def __unpack_data__(self, data):
        """
         Check the key received and calls the procedure associated with the key type
        :param data:
        """
        self.print_helper.debug("__unpack_data")
        try:
            if isinstance(data, dict):

                cluster_name = await self.__process_cluster_name__(data)

                schedules = await self.__process_schedule_report(data[self.k8s_config.schedule_key])

                if self.first_run:
                    backups = await self.__process_first_backups_report(data[self.k8s_config.backup_key])
                else:
                    backups = await self.__process_difference_report(data[self.k8s_config.backup_key])

                messages = dict(cluster_name)
                has_diff = False
                if isinstance(schedules, dict) and len(schedules) > 0:
                    has_diff = True
                    messages.update(schedules)
                if isinstance(backups, dict) and len(backups) > 0:
                    has_diff = True
                    messages.update(backups)
                if has_diff:
                    await self.__send_to_dispatcher(messages)

            else:
                self.print_helper.info(f"__unpack_data.the message is not a type of dict")

            # dispatcher alive message
            # if self.alive_message_seconds > 0:
            #     diff = calendar.timegm(datetime.today().timetuple()) - self.last_send
            #
            #     if diff > self.alive_message_seconds or self.force_alive_message:
            #         self.print_helper.info(f"__unpack_data.send alive message")
            #         await self.send_to_dispatcher(f"Cluster: {self.cluster_name}"
            #                                       f"\nvelero-watchdog is running."
            #                                       f"\nThis is an alive message"
            #                                       f"\nNo warning/errors were triggered in the last "
            #                                       f"{int(self.alive_message_seconds / 3600)} "
            #                                       f"hours ", True)
            #         self.force_alive_message = False

        except Exception as err:
            self.print_helper.error_and_exception(f"__unpack_data", err)

    # @handle_exceptions_method
    # def _extract_days_from_str(self, str_number):
    #     self.print_helper.info("_extract_days_from_str")
    #     value = -1
    #
    #     index = str_number.find('d')
    #
    #     if index != -1:
    #         value = int(str_number.strip()[:index])
    #
    #     if value > 0:
    #         return value
    #     else:
    #         return None

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

    def __pre_batch_data(self, data):
        try:
            self.print_helper.info("_pre_batch_data")
            if len(data) > 0:
                for backup_name, backup_info in data['backups'].items():
                    if 'expire' in backup_info:
                        if len(backup_info['expire']) > 0:
                            day = self.__extract_days_from_str(str(backup_info['expire']))
                            if day > self.k8s_config.EXPIRES_DAYS_WARNING:
                                self.print_helper.debug(
                                        f"_pre_batch_data: "
                                        f"{backup_name}"
                                        f" expire from {data['backups'][backup_name]['expire']}"
                                        f" forced to {self.k8s_config.EXPIRES_DAYS_WARNING}d")
                                data['backups'][backup_name]['expire'] = f"{self.k8s_config.EXPIRES_DAYS_WARNING}d"

            return data
        except Exception as err:
            self.print_helper.error_and_exception(f"__pre_batch_data", err)
            return data

    def __try_to_parse_to_str(self, value):
        self.print_helper.info("__last_backup_report")
        try:
            return str(value)
        except Exception as err:
            self.print_helper.error_and_exception(f"__try_to_parse_to_str", err)
            return value

    async def __process_difference_report(self, data):
        print("__process_difference_report")
        data = self.__pre_batch_data(data)

        backups = data['backups']

        if self.old_backup == data:
            self.print_helper.info("__process_difference_report. do nothing same data")
            return

        old_backups = {}

        if len(self.old_backup) > 0:
            old_backups = self.old_backup['backups']

        backups_diff = self.__find_dict_difference(old_backups, backups)
        print("backups", backups)
        print("backups_diff", backups_diff)

        backup_completed = 0
        backup_in_progress = 0
        backup_failed = 0
        backup_partially_failed = 0
        backup_in_errors = 0
        backup_in_wrn = 0

        message_body = ''
        backup_in_progress_str = ''
        error_str = ''
        wrn_str = ''
        backup_failed_str = ''
        backup_partially_failed_str = ''
        backup_completed_str = ''

        point = '\u2022'
        print("added", backups_diff['added'])
        for backup_name in backups:
            backup_info = backups[backup_name]
            print("backup_name", backup_name)
            if backup_name in backups_diff['added']:
                # add status field
                print(backup_info)
                if len(backup_info['phase']) > 0:
                    if backup_info['phase'].lower() == 'completed':
                        backup_completed += 1
                        backup_completed_str += f'\n\t{str(backup_name)}'
                    elif backup_info['phase'].lower() == 'inprogress':
                        backup_in_progress_str += f'\n\t{str(backup_name)}'
                        backup_in_progress += 1
                    elif backup_info['phase'].lower() == 'failed':
                        backup_failed_str += f'\n\t{str(backup_name)}'
                        backup_failed += 1
                    elif backup_info['phase'].lower() == 'partiallyfailed':
                        backup_partially_failed_str += f'\n\t{str(backup_name)}'
                        backup_partially_failed += 1

                    # add error field
                    error = self.__get_backup_error_message(str(backup_info['errors']))
                    if len(error) > 0:
                        error_str += f'\t{str(backup_name)}'
                        backup_in_errors += 1

                    # add warning field
                    wrn = self.__get_backup_error_message(str(backup_info['warnings']))
                    if len(wrn) > 0:
                        wrn_str += f'\t{str(backup_name)}'
                        backup_in_wrn += 1
        # end stats
        if backup_completed > 0:
            message_body += f'\n{point} Completed={backup_completed}{backup_completed_str}'
        if backup_in_progress > 0:
            message_body += f'\n{point} In Progress={backup_in_progress}{backup_in_progress_str}'
        if backup_in_errors > 0:
            message_body += f'\n{point} With Errors={backup_in_errors}\n{error_str}'
        if backup_in_wrn > 0:
            message_body += f'\n{point} With Warnings={backup_in_wrn}\n{wrn_str}'
        if backup_failed > 0:
            message_body += f'\n{point} Failed={backup_failed}{backup_failed_str}'
        if backup_partially_failed > 0:
            message_body += f'\n{point} Partially Failed={backup_partially_failed}{backup_partially_failed_str}'
        print("--------------------------", message_body)
        self.old_backup = data
        return {'backups': message_body}

    async def __process_first_backups_report(self, data):
        self.print_helper.info("__last_backup_report")
        try:
            # LS 2023.11.19 pre-batch raw data for avoiding unuseful message
            data = self.__pre_batch_data(data)

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

            point = '\u2022'

            #
            # build details messages
            #
            # message = ''
            # for backup_name, backup_info in backups.items():
            #     self.print_helper.debug_if(self.debug_on, f'Backup schedule: {backup_name}')
            #
            #     if backup_name != "error" or 'schedule' in backup_info:
            #         #
            #         # build current state string
            #         #
            #         current_state = str(backup_name) + '\n'
            #
            #         current_state += '\t schedule name=' + self.__try_to_parse_to_str(backup_info['schedule']) + '\n'
            #
            #         # add end at field
            #         if len(backup_info['completion_timestamp']) > 0:
            #             current_state += '\t end at=' + str(backup_info['completion_timestamp']) + '\n'
            #
            #         # add expire field
            #         if len(backup_info['expire']) > 0:
            #             current_state += '\t expire=' + str(backup_info['expire'])
            #
            #             day = self.__extract_days_from_str(str(backup_info['expire']))
            #             if day is None:
            #                 backup_not_retrieved += 1
            #                 current_state += f'**IS NOT VALID{backup_info["expire"]}'
            #             elif day < self.k8s_config.EXPIRES_DAYS_WARNING:
            #                 expired_backup += 1
            #                 backup_expired_str += f'\n\t{str(backup_name)}'
            #                 current_state += '**WARNING'
            #
            #             current_state += '\n'
            #
            #         # add status field
            #         if len(backup_info['phase']) > 0:
            #             current_state += '\t status=' + str(backup_info['phase']) + '\n'
            #             if backup_info['phase'].lower() == 'completed':
            #                 backup_completed += 1
            #             elif backup_info['phase'].lower() == 'inprogress':
            #                 backup_in_progress_str += f'\n\t{str(backup_name)}'
            #                 backup_in_progress += 1
            #             elif backup_info['phase'].lower() == 'failed':
            #                 backup_failed_str += f'\n\t{str(backup_name)}'
            #                 backup_failed += 1
            #             elif backup_info['phase'].lower() == 'partiallyfailed':
            #                 backup_partially_failed_str += f'\n\t{str(backup_name)}'
            #                 backup_partially_failed += 1
            #
            #         # add error field
            #         error = self.__get_backup_error_message(str(backup_info['errors']))
            #         if len(error) > 0:
            #             error_str += f'\t{str(backup_name)}'
            #             current_state += '\t' + ' error=' + error + ' '
            #             backup_in_errors += 1
            #
            #         # add warning field
            #         wrn = self.__get_backup_error_message(str(backup_info['warnings']))
            #         if len(wrn) > 0:
            #             wrn_str += f'\t{str(backup_name)}'
            #             current_state += '\t' + 'warning=' + wrn + '\n'
            #             backup_in_wrn += 1
            #
            #         current_state += '\n'
            #         message += current_state
            #
            # detail_message = f'Backup details [{backup_count}/{unscheduled["counter_all"]}]:\n{message}'

            #
            # calc stats
            #

            for backup_name, backup_info in backups.items():
                self.print_helper.debug(f'Backup schedule: {backup_name}')

                if backup_name != "error" or 'schedule' in backup_info:

                    if len(backup_info['expire']) > 0:

                        day = self.__extract_days_from_str(str(backup_info['expire']))
                        if day is None:
                            backup_not_retrieved += 1
                        elif day < self.k8s_config.EXPIRES_DAYS_WARNING:
                            expired_backup += 1
                            backup_expired_str += f'\n\t{str(backup_name)}'

                    # add status field
                    if len(backup_info['phase']) > 0:
                        if backup_info['phase'].lower() == 'completed':
                            backup_completed += 1
                        elif backup_info['phase'].lower() == 'inprogress':
                            backup_in_progress_str += f'\n\t{str(backup_name)}'
                            backup_in_progress += 1
                        elif backup_info['phase'].lower() == 'failed':
                            backup_failed_str += f'\n\t{str(backup_name)}'
                            backup_failed += 1
                        elif backup_info['phase'].lower() == 'partiallyfailed':
                            backup_partially_failed_str += f'\n\t{str(backup_name)}'
                            backup_partially_failed += 1

                    # add error field
                    error = self.__get_backup_error_message(str(backup_info['errors']))
                    if len(error) > 0:
                        error_str += f'\t{str(backup_name)}'
                        backup_in_errors += 1

                    # add warning field
                    wrn = self.__get_backup_error_message(str(backup_info['warnings']))
                    if len(wrn) > 0:
                        wrn_str += f'\t{str(backup_name)}'
                        backup_in_wrn += 1
            # end stats

            message_header += (f'{point} Namespaces={unscheduled["counter_all"]} \n'
                               f'{point} Unscheduled namespaces={unscheduled["counter"]}\n'
                               f'Backups Stats based on last backup for every schedule and backup without schedule'
                               f'\n{point} Total={backup_count}'
                               f'\n{point} Completed={backup_completed}')

            if backup_in_progress > 0:
                message_header += f'\n{point} In Progress={backup_in_progress}\n{backup_in_progress_str}'

            if backup_in_errors > 0:
                message_body += f'\n{point} With Errors={backup_in_errors}\n{error_str}'
            if backup_in_wrn > 0:
                message_body += f'\n{point} With Warnings={backup_in_wrn}\n{wrn_str}'
            if backup_failed > 0:
                message_body += f'\n{point} Failed={backup_failed}{backup_failed_str}'
            if backup_partially_failed > 0:
                message_body += f'\n{point} Partially Failed={backup_partially_failed}{backup_partially_failed_str}'
            if expired_backup > 0:
                message_body += (f'\n{point} Number of backups in warning period={expired_backup} '
                                 f'[expires day less than {self.k8s_config.EXPIRES_DAYS_WARNING}d]'
                                 f'{backup_expired_str}')

            # build unscheduled namespaces string
            if len(unscheduled) > 0:
                str_namespace = ''
                for name_s in unscheduled['difference']:
                    str_namespace += f'\t{name_s}\n'
                if len(str_namespace) > 0:
                    message = (
                        f'Namespace without active backup [{unscheduled["counter"]}/{unscheduled["counter_all"]}]'
                        f':\n{str_namespace}')

            # if len(out_message) > 10:
            #    await self.send_to_dispatcher(out_message)
            if len(self.old_backup) == 0:
                self.old_backup = data
                return {'backups':  f"{message_header}\n{message_body}\n{message}"}
            else:
                self.old_backup = data
                return {'backups':  message_body}

        except Exception as err:
            # self.print_helper.error(f"consumer error : {err}")
            self.print_helper.error_and_exception(f"__last_backup_report", err)

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
            "old_values": differing_dict1,
            "new_values": differing_dict2,
        }

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
                    message += 'Removed scheduled:'
                    for rem in diff['removed']:
                        message += '\n' + rem

                if len(self.old_schedule_status) > 0 and len(diff['added']) > 0:
                    message += '\nAdded scheduled:'
                    for add in diff['added']:
                        message += '\n' + add

                if len(diff['old_values']) > 0:
                    message += '\nUpdate scheduled:'
                    for schedule_name in diff['old_values']:
                        message += "\nname:" + schedule_name
                        for field in diff['old_values'][schedule_name]:
                            if diff['old_values'][schedule_name][field] != diff['new_values'][schedule_name][field]:
                                message += (f"\n{field}: from {diff['old_values'][schedule_name][field]} "
                                            f"to {diff['new_values'][schedule_name][field]}")

            # await self.send_to_dispatcher(message)

            self.old_schedule_status = data

            return {'schedules': message}

        except Exception as err:
            # self.print_helper.error(f"consumer error : {err}")
            self.print_helper.error_and_exception(f"__process_schedule_report", err)

    async def __process_cluster_name__(self, data):
        """
        Obtain cluster name
        @param data:
        """
        self.print_helper.info(f"__process_cluster_name__")

        nodes_name = data[self.k8s_config.cluster_name_key]

        self.print_helper.info(f"cluster name {nodes_name}")
        # if nodes_name is not None:
        #     self.print_helper.info_if(self.debug_on, f"Flush last message")
        #     # LS 2023.11.04 Send configuration separately
        #     if self.send_config:
        #         await self.send_to_dispatcher(f"Cluster name= {nodes_name}")
        #     else:
        #         await self.send_active_configuration(f"Cluster name= {nodes_name}")

        self.cluster_name = {'cluster_name': nodes_name}
        return self.cluster_name

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
                    await self.__unpack_data__(item)
                    self.first_run = False

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
