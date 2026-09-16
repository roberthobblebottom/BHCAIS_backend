import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import files, users

app = FastAPI()

# is required to make cross-origin requests
# -- i.e., requests that originate from a different protocol, IP address, domain name, or port.
# This is necessary since the vue frontend will run at http://localhost:8080.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ["allowed_origin"]],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=os.environ["prefix"])
app.include_router(files.router, prefix=os.environ["prefix"])


@app.get("/")
def front_page():
    return {"msg": "fastapi backend online"}
