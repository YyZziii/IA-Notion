from fastapi import FastAPI
from router import router

app = FastAPI(title="Dynamic Routing API")
app.include_router(router, prefix="/api")
