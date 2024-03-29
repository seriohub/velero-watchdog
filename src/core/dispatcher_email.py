from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from config.config import Config
from config.config_k8s_process import ConfigK8sProcess
from config.config_dispatcher import ConfigDispatcher

from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_async_method


config_app = Config()


class DispatcherEmail:
    """
    Provide a wrapper for sending data over email
    """

    def __init__(self,
                 queue=None,
                 dispatcher_config: ConfigDispatcher = None,
                 k8s_key_config: ConfigK8sProcess = None):

        self.print_helper = PrintHelper('[core.dispatcher_email]',
                                        level=config_app.get_internal_log_level())

        self.k8s_config = ConfigK8sProcess()
        if k8s_key_config is not None:
            self.k8s_config = k8s_key_config

        self.dispatcher_config = ConfigDispatcher()
        if dispatcher_config is not None:
            self.dispatcher_config = dispatcher_config

        self.queue = queue

    @handle_exceptions_async_method
    async def send_email(self, message):
        """
        Send email func
        @param message: body message
        """
        try:
            self.print_helper.info(f"send_email")
            if self.dispatcher_config.email_enable:
                if ((len(self.dispatcher_config.email_smtp_server) > 0)
                        and (len(self.dispatcher_config.email_smtp_server) > 0)
                        and (len(self.dispatcher_config.email_sender) > 0)
                        and (len(self.dispatcher_config.email_sender_password) > 0)
                        and self.dispatcher_config.email_smtp_port > 0
                        and (len(self.dispatcher_config.email_recipient) > 0)):
                    # Create an email message
                    msg = MIMEMultipart()

                    msg['From'] = self.dispatcher_config.email_sender
                    msg['To'] = self.dispatcher_config.email_recipient
                    msg['Subject'] = 'Velero-watchdog report'
                    # Attach the message
                    msg.attach(MIMEText(message, 'plain'))
                    # Connect to the SMTP server and send the email
                    try:
                        self.print_helper.info(f"server {self.dispatcher_config.email_smtp_server}-"
                                               f"port={self.dispatcher_config.email_smtp_port}")

                        server = smtplib.SMTP(host=self.dispatcher_config.email_smtp_server,
                                              port=self.dispatcher_config.email_smtp_port,
                                              timeout=30)
                        server.starttls()
                        server.login(self.dispatcher_config.email_sender,
                                     self.dispatcher_config.email_sender_password)
                        server.sendmail(self.dispatcher_config.email_sender,
                                        self.dispatcher_config.email_recipient.split(';'),
                                        msg.as_string())
                        server.quit()
                        self.print_helper.info(f"Email sent successfully to {self.dispatcher_config.email_recipient}")
                    except Exception as e:
                        self.print_helper.error(f"send_email in error {str(e)}")
                else:
                    self.print_helper.error(f"email configuration is not complete.")

        except Exception as err:
            self.print_helper.error_and_exception(f"send_email", err)

    @handle_exceptions_async_method
    async def run(self, loop=True):
        """
        Main loop
        """
        try:
            self.print_helper.info(f"email channel notification is active")
            flag = True
            while flag:
                flag = loop
                # get a unit of work
                item = await self.queue.get()

                # check for stop signal
                if item is None:
                    break

                self.print_helper.debug(f"email channel: new element received")

                if item is not None and len(item) > 0:
                    await self.send_email(item)

        except Exception as err:
            self.print_helper.error_and_exception(f"run", err)
