pkill -9 fastapi
cd ~/BHCAIS_backend
source .venv/bin/activate
uv run fastapi run --forwarded-allow-ips="*" > fastapi.log 2>&1 &
