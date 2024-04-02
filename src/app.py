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

@app.get("/info")
async def info():
    res = {'app_name': __app_name__,
           'release_version': f"{__version__}",
           'release_date': f"{__date__}"
           }
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/restart")
async def restart():
    app.task.cancel()
    app.task = asyncio.create_task(app.watchdog_daemon.run())
    res = {'restarted': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)


@app.get("/send-report")
async def report():
    wd = Watchdog(daemon=False)
    await wd.run()
    res = {'sent': 'Done!'}
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)

@app.get("/get-config")
async def get_config():
    res = configHelper.get_env_variables()
    response = SuccessfulRequest(payload=res)
    return JSONResponse(content=response.toJSON(), status_code=200)
