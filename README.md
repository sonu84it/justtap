# Magic Image Studio

Magic Image Studio is a full-stack MVP built with React + Vite on the frontend and FastAPI on the backend. A user can upload an image, pick a one-word style, and generate a transformed result. The project launches in demo mode by default, which means it safely returns the uploaded image while the backend keeps the prompt mapping, storage flow, and AI service integration points ready for a future Vertex AI implementation.

## Features

- Responsive React interface with a polished upload-to-preview flow
- Five one-word style buttons: `magic`, `viral`, `cinematic`, `fantasy`, and `meme`
- Loading, error, and empty states for a friendly MVP experience
- Before/after preview and one-click download
- FastAPI `/generate` endpoint with style-to-prompt mapping
- Google Cloud Storage integration for uploaded and generated images
- Demo mode fallback for local development and early demos
- Placeholder service where live Vertex AI editing can be plugged in later
- Cloud Run-ready Dockerfile that builds the frontend and serves it from FastAPI

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
│           └── storage.py
├── frontend
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src
│       ├── App.jsx
│       ├── main.jsx
│       ├── styles.css
│       └── lib
│           └── api.js
└── README.md
```

## Local Development

### 1. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs on `http://localhost:5173`.

### 2. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

The FastAPI API runs on `http://localhost:8080`.

### 3. Optional local environment variables

Create `backend/.env` if you want to customize the defaults:

```env
APP_ENV=development
DEMO_MODE=true
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
MAX_UPLOAD_SIZE_MB=15
GCS_BUCKET_NAME=
GCS_PUBLIC_BASE_URL=
GOOGLE_CLOUD_PROJECT=
VERTEX_ENABLED=false
VERTEX_LOCATION=us-central1
VERTEX_MODEL=imagegeneration@006
```

### 4. Try the app

1. Open `http://localhost:5173`
2. Upload an image
3. Choose a style
4. Click `Generate Image`
5. Download the result

In demo mode, the app returns the original image so the full UX works before the live AI editing layer is connected.

## Google Cloud Storage

If `GCS_BUCKET_NAME` is set, the backend uploads both the original image and generated result to Google Cloud Storage and returns those URLs to the frontend.

If `GCS_BUCKET_NAME` is not set, the backend falls back to inline `data:` URLs so the MVP still works locally with no cloud dependencies.

Before using GCS:

1. Create a bucket.
2. Grant the runtime service account permission to write objects.
3. If you want browser-accessible URLs, either make the bucket objects readable or serve them through your preferred signed/public URL pattern.
4. Set `GCS_PUBLIC_BASE_URL` if you want to override the default `https://storage.googleapis.com/<bucket>/<object>` URL format.

## Vertex AI Integration Placeholder

The file [backend/app/services/image_transform.py](/Users/sonu/Documents/New project/backend/app/services/image_transform.py) contains two backend paths:

- `DemoTransformService`, which returns the uploaded image unchanged
- `VertexAITransformService`, which is the placeholder for future live image editing

When you are ready to connect Vertex AI:

1. Replace the `transform()` method in [backend/app/services/image_transform.py](/Users/sonu/Documents/New project/backend/app/services/image_transform.py)
2. Keep the existing prompt mapping from [backend/app/prompts.py](/Users/sonu/Documents/New project/backend/app/prompts.py)
3. Set `DEMO_MODE=false`
4. Set `VERTEX_ENABLED=true`
5. Deploy with credentials that can call Vertex AI and write to GCS

## Build and Serve with Docker

The Dockerfile at [backend/Dockerfile](/Users/sonu/Documents/New project/backend/Dockerfile) builds the React frontend first, then packages the FastAPI backend and the built static files into one container.

Build locally:

```bash
docker build -f backend/Dockerfile -t magic-image-studio .
```

Run locally:

```bash
docker run --rm -p 8080:8080 \
  -e DEMO_MODE=true \
  magic-image-studio
```

Open `http://localhost:8080` to use the full app from the single container.

## Deploy to Google Cloud Run

### 1. Set your project

```bash
gcloud config set project YOUR_PROJECT_ID
```

### 2. Create a storage bucket

```bash
gcloud storage buckets create gs://YOUR_MAGIC_IMAGE_BUCKET --location=us-central1
```

### 3. Build the container with Cloud Build

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/magic-image-studio -f backend/Dockerfile .
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy magic-image-studio \
  --image gcr.io/YOUR_PROJECT_ID/magic-image-studio \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DEMO_MODE=true,GCS_BUCKET_NAME=YOUR_MAGIC_IMAGE_BUCKET
```

### 5. For live AI later

When you implement the Vertex AI transform path, redeploy with:

```bash
gcloud run deploy magic-image-studio \
  --image gcr.io/YOUR_PROJECT_ID/magic-image-studio \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DEMO_MODE=false,VERTEX_ENABLED=true,GCS_BUCKET_NAME=YOUR_MAGIC_IMAGE_BUCKET,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
```

Also make sure the Cloud Run service account has:

- `Storage Object Admin` or a narrower bucket write role
- Vertex AI user permissions for the model you plan to call

## Notes for Beginners

- The frontend calls `POST /generate` using `FormData`, so you do not need to manually encode the image.
- The backend keeps style prompt logic separate from API logic, which makes it easier to extend later.
- The storage layer is separate from the transform layer, so you can swap either one independently.
- Demo mode is intentional. It gives you a launchable MVP now instead of blocking on model integration.
