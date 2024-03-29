from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio

from watchdog import Watchdog

app = FastAPI()

app.watchdog_daemon = Watchdog(daemon=True)
app.task = asyncio.create_task(app.watchdog_daemon.run())


@app.get("/")
async def online():
    return JSONResponse(content={'status': 'alive'}, status_code=200)


@app.get("/restart")
async def restart():
    app.task.cancel()
    app.task = asyncio.create_task(app.watchdog_daemon.run())
    return JSONResponse(content={'restarted': 'Done!'}, status_code=200)


@app.get("/report")
async def report():
    wd = Watchdog(daemon=False)
    await wd.run()
    return JSONResponse(content={'send report': 'Done!'}, status_code=200)
