import sys
import asyncio

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from core.kubernetes_status_run import KubernetesStatusRun
from core.velero_checker import VeleroChecker
from core.dispatcher import Dispatcher
from core.dispatcher_telegram import DispatcherTelegram
from core.dispatcher_email import DispatcherEmail

from utils.handle_error import handle_exceptions_async_method
from utils.printer import PrintHelper

from app_data import __version__
from app_data import __date__


config_app = Config()

class Watchdog:

    def __init__(self, daemon):
        self.tasks = []
        self.queue_request = asyncio.Queue()
        self.daemon_mode = daemon
        self.config_prg = Config()

        self.loop_seconds = self.config_prg.process_run_sec()
        self.clk8s_setup_disp = ConfigDispatcher(self.config_prg)
        self.clk8s_setup = ConfigK8sProcess(self.config_prg)

        self.print_helper = PrintHelper('[common.routers.health]',
                                        level=config_app.get_internal_log_level())

    @handle_exceptions_async_method
    async def restart(self):
        for task in self.tasks:
            task.cancel()
        await self.run()

    @handle_exceptions_async_method
    async def report(self):
        await self.queue_request.put(1)

    @handle_exceptions_async_method
    async def run(self):
        daemon = self.daemon_mode
        seconds = self.loop_seconds
        disp_class = self.clk8s_setup_disp
        k8s_class = self.clk8s_setup

        # create the shared queue
        tasks = []
        queue_data = asyncio.Queue()
        queue_dispatcher = asyncio.Queue()
        queue_dispatcher_telegram = asyncio.Queue()
        queue_dispatcher_mail = asyncio.Queue()

        tasks.append(KubernetesStatusRun(queue_request=self.queue_request,
                                         queue=queue_data,
                                         cycles_seconds=seconds,
                                         k8s_key_config=k8s_class))
        k8s_stat_read = tasks[-1]

        tasks.append(VeleroChecker(queue=queue_data,
                                   dispatcher_queue=queue_dispatcher,
                                   dispatcher_max_msg_len=disp_class.max_msg_len,
                                   dispatcher_alive_message_hours=disp_class.alive_message,
                                   k8s_key_config=k8s_class
                                   ))
        velero_stat_checker = tasks[-1]

        tasks.append(Dispatcher(queue=queue_dispatcher,
                                queue_telegram=queue_dispatcher_telegram,
                                queue_mail=queue_dispatcher_mail,
                                dispatcher_config=disp_class,
                                k8s_key_config=k8s_class
                                ))
        dispatcher_main = tasks[-1]

        tasks.append(DispatcherTelegram(queue=queue_dispatcher_telegram,
                                        dispatcher_config=disp_class,
                                        k8s_key_config=k8s_class
                                        ))
        dispatcher_telegram = tasks[-1]

        tasks.append(DispatcherEmail(queue=queue_dispatcher_mail,
                                     dispatcher_config=disp_class,
                                     k8s_key_config=k8s_class
                                     ))
        dispatcher_mail = tasks[-1]
        try:

            if daemon:
                await asyncio.gather(*[t.run() for t in tasks])
                self.tasks = tasks
            else:
                await k8s_stat_read.run(loop=False)
                await velero_stat_checker.run(loop=False)
                await dispatcher_main.run(loop=False)
                if self.config_prg.telegram_enable():
                    await dispatcher_telegram.run(loop=False)
                if self.config_prg.email_enable():
                    await dispatcher_mail.run(loop=False)

        except KeyboardInterrupt:
            self.print_helper.wrn("user request stop")
            pass
        except Exception as e:
            self.print_helper.error_and_exception(f"main_start", e)


if __name__ == "__main__":
    print(f"INFO    [SYSTEM] start application version {__version__} release date {__date__}")

    daemon_mode = False
    if len(sys.argv) > 1 and '--daemon' in sys.argv:
        daemon_mode = True

    watchdog = Watchdog(daemon=daemon_mode)
    asyncio.run(watchdog.run())
