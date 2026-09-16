pkill -9 fastapi
cd ~/BHCAIS_backend
source .venv/bin/activate
fastapi run > fastapi.log 2>&1 &
