from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.routes import files, users

app = FastAPI()
# is required to make cross-origin requests
# -- i.e., requests that originate from a different protocol, IP address, domain name, or port.
# This is necessary since the vue frontend will run at http://localhost:8080.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://167.172.76.229:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router,prefix='/api')
app.include_router(files.router,prefix='/api')
app.mount("/",StaticFiles(directory="/root/BHCAIS_frontend/dist",html=True),name="static")

@app.get("/")
def front_page():
    return {"msg": "fastapi backend online"}
