# Parcial 3 – Algoritmos - IA

Desarrollo del tercer parcial del curso de Algoritmos - Inteligencia Artificial.

## Backend (FastAPI)

Servicio base en `backend/` (Python 3.12+, FastAPI). Endpoints:

| Ruta | Descripción |
|------|-------------|
| `GET /health` | Liveness: `{"status": "ok"}` |
| `GET /docs` | Documentación OpenAPI interactiva |
| `/api/v1/...` | Prefijo para los endpoints de negocio (aún vacío) |

Cada respuesta incluye el header `X-Request-ID` (se reutiliza el enviado por el cliente si es válido) y cada petición se registra como una línea JSON en stdout.

## Cómo ejecutar el proyecto

### Requisitos

| Herramienta | Versión | Necesaria para |
|-------------|---------|----------------|
| Git | cualquiera | clonar el repo |
| Docker Desktop (o Docker Engine + Compose v2) | Compose ≥ 2.24 | ejecución con Docker |
| Python | 3.12 o superior | ejecución sin Docker y pruebas |

Con Docker no necesitas instalar Python.

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd Parcial-3-Algoritmos-IA
```

### 2. Configurar variables de entorno (opcional)

El servicio arranca con valores por defecto. Para cambiarlos:

```bash
cp .env.example .env         # Windows (PowerShell): Copy-Item .env.example .env
```

Edita `.env` según la tabla de [Configuración](#configuración). El `.env` real nunca se versiona.

### 3a. Ejecutar con Docker (recomendado)

Abre Docker Desktop y espera a que el engine esté corriendo. Luego, desde la raíz del repo:

```bash
docker compose up --build
```

- Backend en <http://localhost:8000> y documentación en <http://localhost:8000/docs>.
- El código de `backend/app` está montado: al guardar un archivo el servicio recarga solo.
- Para correrlo en segundo plano: `docker compose up --build -d` y ver logs con `docker compose logs -f backend`.
- Para detenerlo: `Ctrl+C` (o `docker compose down` si usaste `-d`).

### 3b. Ejecutar sin Docker

Desde la carpeta `backend/`:

```bash
cd backend
python -m venv .venv
```

Activa el entorno virtual:

```bash
.venv\Scripts\activate        # Windows (cmd/PowerShell)
source .venv/bin/activate     # Linux / macOS / Git Bash: source .venv/Scripts/activate
```

Instala dependencias y arranca:

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

El servicio queda en <http://127.0.0.1:8000>. Para detenerlo: `Ctrl+C`. Si tienes un `.env` en la raíz, cópialo o exporta las variables en `backend/`, porque sin Docker se lee `.env` desde el directorio donde corres `uvicorn`.

### 4. Verificar que funciona

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

O abre <http://localhost:8000/docs> en el navegador. Con la respuesta incluyes el header `X-Request-ID`:

```bash
curl -i -H "X-Request-ID: mi-prueba-1" http://localhost:8000/health
```

### Pruebas

Con el entorno virtual activo, desde `backend/`:

```bash
pytest
```

### Configuración

Variables de entorno (ver `.env.example`):

| Variable | Valores | Default |
|----------|---------|---------|
| `APP_NAME` | texto | `Parcial-P3-Algoritmos-IA` |
| `ENVIRONMENT` | `local`, `staging`, `production` | `local` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `API_V1_PREFIX` | ruta | `/api/v1` |

Un valor inválido hace que el servicio falle al iniciar indicando la variable.

### Problemas frecuentes

| Síntoma | Causa y solución |
|---------|------------------|
| `failed to connect to the docker API` | Docker Desktop no está corriendo. Ábrelo y espera a "Engine running". |
| `port is already allocated` / puerto 8000 ocupado | Otro proceso usa el 8000. Ciérralo o cambia el mapeo en `docker-compose.yml` (por ejemplo `"8001:8000"`). |
| `ValidationError ... log_level` al iniciar | Valor inválido en `.env`. Usa uno de los valores de la tabla de configuración. |
| `env_file ... required` no soportado | Compose antiguo. Actualiza Docker Desktop (Compose ≥ 2.24). |
| La recarga no detecta cambios en Windows | Se usa un recargador por polling; espera 1–2 segundos tras guardar. |
