import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.routes import files, users

load_dotenv()
app = FastAPI()
# is required to make cross-origin requests
# -- i.e., requests that originate from a different protocol, IP address, domain name, or port.
# This is necessary since the vue frontend will run at http://localhost:8080.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("allowed_origin")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=os.getenv("prefix"))
app.include_router(files.router, prefix=os.getenv("prefix"))


@app.get("/")
def front_page():
    return {"msg": "fastapi backend online"}
print(f"is_production env: '{os.getenv('is_production')}'")
print(f"Type: {type(os.getenv('is_production'))}")
print(f"Comparison result: {os.getenv('is_production') == 'true'}")

if os.getenv("is_production","false").lower() == "true":
    app.frontend(
        "/",
    directory="/root/BHCAIS_frontend/dist",
    )
