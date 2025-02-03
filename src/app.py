import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app_data import __app_name__, __version__, __date__
import asyncio
from core.dispatcher_apprise import DispatcherApprise

from api.common.response_model.successful_request import SuccessfulRequest
from api.schemas.apprise_test_provider import AppriseTestService

from watchdog import Watchdog
from config.config import Config, get_configmap

app = FastAPI()

configHelper = Config()


def load_user_config():
    global configHelper

    # if str(os.getenv('ENV')).lower() == 'development':
    #
    #     cm = get_configmap(namespace=os.getenv('K8S_VELERO_UI_NAMESPACE', 'velero-ui'),
    #                        configmap_name='velero-watchdog-config')
    #
    #     # Update environment variables
    #     for key, value in cm.items():
    #         if (key != 'K8S_IN_CLUSTER_MODE' and
    #                 key != 'PROCESS_KUBE_CONFIG' and
    #                 key != 'PROCESS_LOAD_KUBE_CONFIG' and
    #                 key != 'PROCESS_CYCLE_SEC'):
    #             os.environ[key] = value

    print("\nAdd user configs environment")
    cm = get_configmap(namespace=os.getenv('K8S_VELERO_UI_NAMESPACE', 'velero-ui'),
                       configmap_name='velero-watchdog-user-config')
    if cm:
        # Update environment variables
        # for key, value in cm.items():
        #     print(key, value)
        #     os.environ[key] = value
        # Update environment variables
        for key, value in cm.items():
            print(key, value)
            os.environ[key] = value

        # env_file = ".env"
        # env_data = {}
        # if os.path.exists(env_file):
        #     with open(env_file, "r") as f:
        #         for line in f:
        #             if "=" in line:
        #                 key, value = line.strip().split("=", 1)
        #                 env_data[key] = value  # Manteniamo le vecchie variabili
        #
        # # Aggiorna o aggiunge le variabili di os.environ
        # for key, value in cm.items():
        #     env_data[key] = value  # Sovrascrive se esiste, altrimenti aggiunge
        #
        # # Scrive tutte le variabili aggiornate nel file .env
        # with open(env_file, "w") as f:
        #     for key, value in env_data.items():
        #         f.write(f"{key}={value}\n")
    print("\n")
    configHelper = Config()


load_user_config()

app.watchdog_daemon = Watchdog(daemon=True)
app.task = asyncio.create_task(app.watchdog_daemon.run())


@app.get("/")
async def online():
    return JSONResponse(content={'status': 'alive'}, status_code=200)


@app.get("/info",
         tags=['System'],
         summary='Get information about the system')
async def info():
    res = {'app_name': __app_name__,
           'release_version': f"{__version__}",
           'release_date': f"{__date__}"
           }
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.post("/restart",
          tags=['System'],
          summary='Restart service')
async def restart():
    print("\n\nRestart watchdog daemon\n\n")
    app.task.cancel()
    load_user_config()
    app.watchdog_daemon = Watchdog(daemon=True)
    app.task = asyncio.create_task(app.watchdog_daemon.run())
    res = {'restarted': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.post("/send-report",
          tags=['Run'],
          summary='Send report')
async def report():
    wd = Watchdog(daemon=False)
    await wd.run()
    res = {'sent': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/environment",
         tags=['System'],
         summary='Get the current configuration')
async def get_config():
    # res = configHelper.get_env_variables()
    res = app.watchdog_daemon.get_env()
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.post("/test-service",
          tags=['Run'],
          summary='Send a test message to verify channel settings')
async def send_test_notification(provider: AppriseTestService):
    dispatcher_test = DispatcherApprise(queue=None, dispatcher_config=None, test_configs=provider.config)
    success = await dispatcher_test.send_msgs(message='Test message success sent!', test_message=True)
    res = {'success': success}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)
