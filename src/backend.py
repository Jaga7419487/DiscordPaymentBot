import uvicorn
from fastapi import FastAPI


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/keep_alive")
async def keep_alive():
    return {"message": "I'm alive!"}


async def start_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()
