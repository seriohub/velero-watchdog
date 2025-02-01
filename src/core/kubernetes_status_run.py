import asyncio

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess

from core.velero_status import VeleroStatus

from utils.handle_error import handle_exceptions_async_method

from utils.logger import ColoredLogger, LEVEL_MAPPING
import logging

config_app = Config()
logger = ColoredLogger.get_logger(__name__, level=LEVEL_MAPPING.get(config_app.get_internal_log_level(), logging.INFO))


class KubernetesStatusRun:
    """
    Invoke the state of k8s items cyclically
    """

    def __init__(self,
                 queue_request=None,
                 queue=None,
                 cycles_seconds: int = 120,
                 k8s_key_config: ConfigK8sProcess = None):

        self.queue = queue
        self.queue_request = queue_request
        self.cycle_seconds = cycles_seconds
        self.loop = 0

        self.velero_stat = VeleroStatus(k8s_key_config)

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

    @handle_exceptions_async_method
    async def __put_in_queue(self, obj):
        """
        Add object to a queue
        @param obj: data to add in the queue
        """
        # self.print_helper.debug("__put_in_queue__")

        await self.queue.put(obj)

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        Main loop
        """
        # self.print_helper.info(f"start main procedure seconds {self.cycle_seconds}")
        logger.info(f"Start kubernetes status...")

        # add wait
        await asyncio.sleep(2)

        cluster_name = self.k8s_config.cluster_id

        flag = True
        while flag:
            flag = loop
            try:
                logger.debug(f"Kubernetes status cycle in seconds every {self.cycle_seconds}")
                data_res = {self.k8s_config.cluster_name_key: cluster_name}

                if self.k8s_config.schedule_enable:
                    schedule_list = self.velero_stat.get_k8s_velero_schedules(
                        namespace=config_app.get_k8s_velero_namespace())
                    data_res[self.k8s_config.schedules_key] = schedule_list

                if self.k8s_config.backup_enable:
                    last_backups_list = self.velero_stat.get_k8s_last_backups(
                        namespace=config_app.get_k8s_velero_namespace())
                    data_res[self.k8s_config.backups_key] = last_backups_list[self.k8s_config.backups_key]

                    unscheduled_namespace = self.velero_stat.get_unscheduled_namespaces()  # (
                    # namespace=config_app.get_k8s_velero_namespace())
                    data_res[self.k8s_config.unschedule_namespace_key] = unscheduled_namespace[
                        self.k8s_config.unschedule_namespace_key]

                    all_backups = self.velero_stat.get_k8s_all_backups(namespace=config_app.get_k8s_velero_namespace())
                    data_res[self.k8s_config.all_backups_key] = all_backups[self.k8s_config.all_backups_key]

                await self.__put_in_queue(data_res)

                if loop:
                    await asyncio.sleep(self.cycle_seconds)

            except Exception as e:
                logger.error(f"Kubernetes status run: {str(e)}")
