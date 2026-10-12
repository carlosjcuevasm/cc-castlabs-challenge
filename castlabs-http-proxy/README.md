# Castlabs HTTP Proxy

An asynchronous HTTP proxy built with Python 3.11+ and FastAPI. It generates an HS512-signed JWT for incoming POST requests, attaches it as the `x-my-jwt` header, and forwards the request to an upstream endpoint.

## Features
All requested behaviours
- Asynchronous HTTP forwarding with HTTPX.
- JWT generation with `iat`, `jti`, and `payload` claims.
- Configurable upstream URL and listening port.
- Docker Compose deployment.
- Status endpoint with uptime and proxy request count.
- Automated tests for JWT generation, proxy behavior and status endpoint.

## Requirements

- Python 3.11+
- Docker Engine (tested on 29.9.0)(assignment targets last two stable versions)
- Docker Compose
- GNU Make

## Configuration

Create your local environment file:

```bash
cp .env.example .env
```

Configure these variables:

| Variable | Required | Default |
|---|---|---|
| `JWT_SECRET_HEX` | Yes | None |
| `UPSTREAM_URL` | No | `https://postman-echo.com/post` |

Set `JWT_SECRET_HEX` to the secret provided in the challenge.

## Run with Docker

From the project root:

```bash
make build
make run
```

The proxy listens on port `8000` by default. To use another port:

```bash
HTTP_PORT=9000 make run
```

Open the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs). If you selected another port, replace `8000` accordingly.

Press `Ctrl+C` to stop the service.

## Run locally

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ensure `JWT_SECRET_HEX` and `UPSTREAM_URL` are available in the environment or `.env`.

## API

### `POST /proxy`

Accepts a JSON object containing a non-empty `username`. Additional JSON fields are allowed and forwarded to the upstream endpoint.

Example:

```bash
curl -X POST http://localhost:8000/proxy \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","message":"hello"}'
```

The proxy attaches a JWT in the `x-my-jwt` header and returns the upstream response body, status code, and content type.

### `GET /status`
Returns the application's uptime in seconds and the number of requests made to `/proxy`, including requests that fail validation or encounter upstream errors.
Example:
```bash
curl http://localhost:8000/status
```
Example response:
```json
{
  "uptime_seconds": 42.31,
  "request_count": 3
}
```
The request count and uptime reset when the application restarts. Requests to `/status` are not included in the proxy request count.

### JWT claims

```json
{
  "iat": 1791763200,
  "jti": "example-random-identifier",
  "payload": {
    "user": "alice",
    "date": "2026-10-12"
  }
}
```

- `iat`: Token issuance time as a Unix timestamp in seconds.
- `jti`: Cryptographically random token identifier.
- `payload.user`: Username from the request.
- `payload.date`: Current UTC date in `YYYY-MM-DD` format.

The token is signed using HS512. JWT payloads are encoded, not encrypted.

## Testing
Run the automated tests with:
```bash
make test
```
The tests cover JWT claims and identifier uniqueness, request forwarding, JWT attachment, upstream response handling, upstream connection failures, request validation, and status reporting.

## Makefile

| Command | Description |
|---|---|
| `make build` | Build the Docker image |
| `make run` | Start the proxy using Docker Compose |
| `make test` | Run the automated test suite |

## Notes

The file `notes-http-proxy-logseq-interactive.html` contains development notes documenting some of the implementation process and my design decisions.

Open it in a browser alongside your IDE for the best experience. It is an interactive HTML export from a PKM (Logseq)
