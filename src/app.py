from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app_data import __app_name__, __version__, __date__
import asyncio

from api.common.response_model.successful_request import SuccessfulRequest
from watchdog import Watchdog
from config.config import Config

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


@app.get("/restart",
         tags=['System'],
         summary='Restart service')
async def restart():
    app.task.cancel()
    app.task = asyncio.create_task(app.watchdog_daemon.run())
    res = {'restarted': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/send-report",
         tags=['Run'],
         summary='Send report')
async def report():
    wd = Watchdog(daemon=False)
    await wd.run()
    res = {'sent': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/get-config",
         tags=['System'],
         summary='Get the current configuration')
async def get_config():
    res = configHelper.get_env_variables()
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/send-test-notification",
         tags=['Run'],
         summary='Send a test message to verify channel settings')
async def send_test_notification(email: bool = True,
                                 telegram: bool = True,
                                 slack: bool = True):
    wd = Watchdog(daemon=False)
    await wd.run(test_notification=True,
                 test_email=email,
                 test_telegram=telegram,
                 test_slack=slack)
    res = {'sent': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)
