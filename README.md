# JustTap

JustTap is a full-stack MVP for one-tap AI image styling. Users upload a photo, choose a single-word style, and generate a transformed result through a React + Vite frontend and a FastAPI backend.

The project supports both demo mode and live Vertex AI image editing. In local development you can still run safely in demo mode, while the deployed backend can run with live Vertex AI editing enabled.

## Features

- Polished responsive interface for desktop, Android, and iPhone-sized screens
- One-page layout with upload, style selection, preview, and download actions
- Five style options: `magic`, `viral`, `cinematic`, `fantasy`, and `meme`
- Anonymous daily usage limit to protect the MVP before login is added
- FastAPI `/generate` endpoint with backend prompt mapping
- Google Cloud Storage support for uploaded and generated images
- Auto-resizing for oversized phone photos before generation
- Live Vertex AI image editing with per-style guidance tuning
- Structured usage logging for Cloud Logging and BigQuery export
- Cloud Run-ready backend container

## Live Deployment

- Frontend: `https://onetap-ai.uc.r.appspot.com`
- Backend: `https://magic-image-studio-api-486899779484.us-central1.run.app`

## Project Structure

```text
.
├── backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app
│       ├── config.py
│       ├── main.py
│       ├── models.py
│       ├── prompts.py
│       └── services
│           ├── image_transform.py
│           ├── storage.py
│           └── usage_limits.py
├── frontend
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src
│       ├── App.jsx
│       ├── main.jsx
│       ├── styles.css
│       └── lib
│           └── api.js
└── README.md
```

## Run Locally

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs on `http://localhost:5173`.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

The API runs on `http://localhost:8080`.

## Environment Variables

Create `backend/.env` if you want to override defaults:

```env
APP_ENV=development
DEMO_MODE=true
DAILY_GENERATION_LIMIT=10
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
MAX_UPLOAD_SIZE_MB=5
MAX_IMAGE_WIDTH=2048
MAX_IMAGE_HEIGHT=2048
MAX_IMAGE_MEGAPIXELS=12
GCS_BUCKET_NAME=
GCS_PUBLIC_BASE_URL=
GOOGLE_CLOUD_PROJECT=
VERTEX_ENABLED=false
VERTEX_LOCATION=us-central1
VERTEX_MODEL=imagen-3.0-capability-001
VERTEX_OUTPUT_MIME_TYPE=image/png
VERTEX_GUIDANCE_SCALE=18
VERTEX_GUIDANCE_SCALES={"cinematic":15,"magic":16,"viral":18,"fantasy":19,"meme":19}
VERTEX_NEGATIVE_PROMPT=blurry, distorted, low quality, extra limbs, duplicated features, warped face, unreadable text, watermark, logo, frame
VERTEX_SAFETY_FILTER_LEVEL=block_some
VERTEX_PERSON_GENERATION=allow_adult
```

Create `frontend/.env` if the frontend should call a deployed backend:

```env
VITE_API_BASE=https://your-cloud-run-service-url
```

## Anonymous Daily Limit

Until authentication is added, JustTap limits how many images a user can generate in a day.

- The backend uses the request IP as a lightweight anonymous identifier.
- If Google Cloud Storage is configured, daily counts are stored in the bucket for better persistence across restarts.
- If GCS is not configured, the app falls back to in-memory tracking for local development.
- When the limit is reached, the API returns `429 Too Many Requests`.

This is a practical MVP safeguard, not a strict anti-abuse system. Once login is added, the same limit can move to per-user tracking.

## Usage Reporting

Every `/generate` request now writes a structured JSON usage event to application logs. These events are designed for Cloud Logging and can be routed to BigQuery later if you want dashboards or long-term reporting.

Tracked fields include:

- `request_id`
- `timestamp` from the Cloud Logging entry
- `client_ip`
- `style_selected`
- `status` such as `success`, `failed`, or `blocked`
- `error_message`
- `original_filename`
- `file_size_bytes`
- `original_image_width` and `original_image_height`
- `image_width` and `image_height`
- `prompt`
- `stored_input_path`
- `stored_output_path`
- `output_filename`
- `used_today`, `remaining_generations`, and `daily_limit`
- `origin`, `user_agent`, `demo_mode`, `vertex_enabled`, `model_name`, and `guidance_scale`

This makes it much easier to answer questions like which styles are most used, which IPs hit limits, which failures are most common, and which storage objects belong to each request.

The project now also supports exporting these usage logs from Cloud Logging into BigQuery for SQL-based reporting.

## Image Guardrails

To control storage and future model costs, the backend enforces a `5 MB` upload limit and normalizes oversized images before generation:

- Maximum file size: `5 MB`
- Working image dimensions: `2048x2048`
- Working resolution: `12 megapixels`

If a user uploads a larger phone photo, the backend resizes it automatically to fit these limits instead of rejecting it outright. These values can be tuned with `MAX_UPLOAD_SIZE_MB`, `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT`, and `MAX_IMAGE_MEGAPIXELS`.

## Demo Mode and Vertex AI

`backend/app/services/image_transform.py` currently contains two paths:

- `DemoTransformService`, which returns the uploaded image unchanged
- `VertexAITransformService`, which calls Vertex AI Imagen image editing when live mode is enabled

To enable live model editing:

1. Enable the Vertex AI API in your Google Cloud project
2. Set `DEMO_MODE=false`
3. Set `VERTEX_ENABLED=true`
4. Set `GOOGLE_CLOUD_PROJECT` to your project ID
5. Deploy with credentials that can call Vertex AI and read and write to GCS

The backend uses the official Vertex AI Python SDK and the Imagen editing-capable model `imagen-3.0-capability-001`. Google’s current docs note that older Imagen 1 and 2 model IDs such as `imagegeneration@006` are deprecated and removed, so this project now uses the current supported editing model instead.

Each style can also use its own `guidance_scale`, which helps balance how strongly the model transforms the image versus how closely it preserves the original subject.

## Google Cloud Storage

If `GCS_BUCKET_NAME` is set, the backend stores both uploaded and generated files in Google Cloud Storage.

If `GCS_BUCKET_NAME` is not set, the backend falls back to inline `data:` URLs so the app still works locally without cloud storage.

Before using GCS:

1. Create a bucket
2. Grant the runtime service account permission to read and write objects
3. Set `GCS_PUBLIC_BASE_URL` only if you want to override the default asset URL pattern

## Deploy to Cloud Run

Build the backend container:

```bash
cd backend
gcloud builds submit --project=YOUR_PROJECT_ID --tag gcr.io/YOUR_PROJECT_ID/magic-image-studio-api .
```

Deploy the service:

```bash
gcloud run deploy magic-image-studio-api \
  --project=YOUR_PROJECT_ID \
  --image gcr.io/YOUR_PROJECT_ID/magic-image-studio-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DEMO_MODE=true,DAILY_GENERATION_LIMIT=10,GCS_BUCKET_NAME=YOUR_BUCKET_NAME,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
```

When live AI is ready, redeploy with:

```bash
gcloud run deploy magic-image-studio-api \
  --project=YOUR_PROJECT_ID \
  --image gcr.io/YOUR_PROJECT_ID/magic-image-studio-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DEMO_MODE=false,VERTEX_ENABLED=true,DAILY_GENERATION_LIMIT=10,GCS_BUCKET_NAME=YOUR_BUCKET_NAME,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,VERTEX_MODEL=imagen-3.0-capability-001
```

## Frontend Deployment

The frontend can be deployed separately using the included App Engine config in `frontend/app.yaml`.

Build and deploy from the `frontend` directory:

```bash
cd frontend
npm install
npm run build
gcloud app deploy
```

## BigQuery Usage Analytics

This project now supports exporting structured usage logs into BigQuery for SQL reporting.

Example setup used in production:

- Dataset: `onetap-ai.magic_image_usage`
- Cloud Logging sink: `magic-image-usage-to-bigquery`

After the sink is active and new events are generated, you can query exported usage logs with SQL in BigQuery.

## Notes

- The frontend calls `POST /generate` with `FormData`, so image upload stays simple.
- Prompt mapping, storage, transform logic, usage limiting, and usage logging are intentionally separated to keep the project beginner-friendly.
- Demo mode still exists for safe local development, but the deployed app can now run with live Vertex AI image editing.
