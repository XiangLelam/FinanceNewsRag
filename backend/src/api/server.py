from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.route import router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

app.mount("/", StaticFiles(directory="frontend_build", html=True), name="frontend")
