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
    res = await app.watchdog_daemon.get_env()
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
