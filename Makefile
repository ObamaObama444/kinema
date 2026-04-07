BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
NGROK_API_URL ?= http://127.0.0.1:4040/api/tunnels
RUNTIME_TUNNEL_URL_FILE ?= .codex-runtime/backend-tunnel-url.txt

UVICORN := ./.venv/bin/uvicorn
PYTHON := ./.venv/bin/python
VERCEL := vercel
BOOTSTRAP_PYTHON ?= python3

.PHONY: backend backend-stable frontend-dev backend-tunnel backend-tunnel-ngrok backend-tunnel-localhostrun frontend-tunnel sync-backend-url sync-asset-version deploy-frontend deploy-miniapp miniapp-status telegram-bot setup-local tg-miniapp

backend:
	$(UVICORN) app.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

backend-stable:
	$(UVICORN) app.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend-dev:
	cd frontend && $(VERCEL) dev --listen 0.0.0.0:$(FRONTEND_PORT) -A vercel.dev.json -y

backend-tunnel:
	ngrok http http://127.0.0.1:$(BACKEND_PORT)

backend-tunnel-ngrok:
	ngrok http http://127.0.0.1:$(BACKEND_PORT)

backend-tunnel-localhostrun:
	$(PYTHON) scripts/start_localhost_run_tunnel.py --port $(BACKEND_PORT) --url-file "$(RUNTIME_TUNNEL_URL_FILE)"

frontend-tunnel:
	ngrok http http://127.0.0.1:$(FRONTEND_PORT)

sync-backend-url:
	if [ -n "$(BACKEND_TUNNEL_URL)" ]; then \
		$(PYTHON) scripts/update_vercel_backend_url.py --url "$(BACKEND_TUNNEL_URL)"; \
	else \
		$(PYTHON) scripts/update_vercel_backend_url.py --auto --runtime-url-file "$(RUNTIME_TUNNEL_URL_FILE)" --ngrok-api-url "$(NGROK_API_URL)" --port "$(BACKEND_PORT)"; \
	fi

sync-asset-version:
	$(PYTHON) scripts/sync_asset_version.py --bump

deploy-frontend: sync-asset-version
	cd frontend && $(VERCEL) deploy --prod -y

deploy-miniapp: sync-backend-url sync-asset-version
	cd frontend && $(VERCEL) deploy --prod -y

miniapp-status:
	@printf "Local backend: " && curl -fsS http://127.0.0.1:$(BACKEND_PORT)/health || true
	@printf "\nTunnel URL file: " && cat "$(RUNTIME_TUNNEL_URL_FILE)" 2>/dev/null || true
	@printf "\nVercel health:\n" && curl -i -sS https://frontend-nine-psi-85.vercel.app/health | sed -n '1,12p' || true

telegram-bot:
	$(PYTHON) scripts/telegram_bot.py

setup-local:
	$(BOOTSTRAP_PYTHON) scripts/dev_telegram_miniapp.py bootstrap

tg-miniapp:
	$(BOOTSTRAP_PYTHON) scripts/dev_telegram_miniapp.py run --host $(BACKEND_HOST) --port $(BACKEND_PORT)
