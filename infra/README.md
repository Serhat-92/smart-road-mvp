# Infra

Operational scripts, launch assets, and local container orchestration live here.

## Docker Compose

The local development stack is defined in [docker-compose.yml](/C:/Users/cifci/OneDrive/Desktop/Projeler/5G%20Destekli%20Akıllı%20Yol%20Güvenliği%20ve%20İhlal%20Tespit%20Sistemi/infra/docker-compose.yml).

1. Copy [`.env.example`](/C:/Users/cifci/OneDrive/Desktop/Projeler/5G%20Destekli%20Akıllı%20Yol%20Güvenliği%20ve%20İhlal%20Tespit%20Sistemi/infra/.env.example) to `infra/.env`.
2. Run `docker compose -f infra/docker-compose.yml up --build`.

The stack starts:

- `gateway-api` on port `8080`
- `ai-inference` on port `8090`
- `command-center` on port `8000`
- `operator-dashboard` on port `5173`
- `postgres` on port `5432`
- `redis` on port `6379`

By default, the gateway seeds demo devices and events for local development, and
the dashboard is configured to talk to the FastAPI backend instead of mock data.
