# Deployment Guide

## Option A) Render Blueprint (recommended)

This deploys both backend and frontend on Render using render.yaml.

1) Push the repo to GitHub or GitLab.
2) In Render: New > Blueprint, select the repo, and apply the blueprint.
3) Set required secrets in the Render dashboard:
	- GEMINI_API_KEY
	- OPENAI_API_KEY
4) (Optional) Increase the disk size for /app/outputs if you generate large videos.

Notes:
- Backend uses RENDER_EXTERNAL_URL automatically for public video links. Set PUBLIC_BASE_URL only if you deploy elsewhere.
- CORS_ORIGINS and BACKEND_API_URL are wired by the blueprint using Render service URLs.
- Outputs are stored on a persistent disk mounted at /app/outputs.

## Option B) Docker Hub + Render + Netlify (legacy)

This guide matches your target setup:
- Backend image pushed to Docker Hub
- Backend deployed on Render as a Web Service (from Docker image)
- Frontend deployed on Netlify (Next.js)

## 1) Build and push backend image to Docker Hub

From repository root:

```bash
docker login
docker build -f backend/Dockerfile -t chandrakarab/text2video-backend:latest backend
docker push chandrakarab/text2video-backend:latest
```

Optional versioned tag:

```bash
docker tag <dockerhub-username>/text2video-backend:latest <dockerhub-username>/text2video-backend:v1
docker push <dockerhub-username>/text2video-backend:v1
```

## 2) Deploy backend on Render

In Render:
1. New > Web Service
2. Choose "Deploy an existing image from a registry"
3. Image URL: `docker.io/<dockerhub-username>/text2video-backend:latest`
4. Instance type: choose based on workload

Set these environment variables in Render:
- PUBLIC_BASE_URL=https://<your-render-backend-domain> (optional on Render)
- CORS_ORIGINS=https://<your-netlify-site-domain>
- GEMINI_API_KEY=<your_key>
- OPENAI_API_KEY=<your_key>

Notes:
- Container now supports Render dynamic port via PORT env automatically.
- Health check path can be /.
- Backend URL format will be like https://your-service-name.onrender.com.

Test backend after deploy:

```bash
curl https://<your-render-backend-domain>/
```

## 3) Deploy frontend on Netlify

Create a new Netlify site from your Git repository and set:

- Build command: pnpm build
- Publish directory: leave empty for Next.js on Netlify

Set these environment variables in Netlify:
- BACKEND_API_URL=https://<your-render-backend-domain>
- NEXT_PUBLIC_API_URL=https://<your-render-backend-domain> (optional; only if calling backend directly from the browser)

Then trigger deploy.

## 4) Verify end-to-end

1. Open your Netlify URL.
2. Submit a prompt.
3. Confirm network calls go to Netlify API routes and then Render backend.
4. Check Render logs for job progress.

## 5) Important production notes

- Render ephemeral filesystem: generated videos in backend/outputs may be lost on restart unless you use a persistent disk.
- For durable storage, move final videos to object storage (S3/R2/GCS) and return that public URL.
- Keep CORS_ORIGINS strict to your Netlify domain(s).

## 6) Updating backend release

```bash
docker build -f backend/Dockerfile -t <dockerhub-username>/text2video-backend:latest backend
docker push <dockerhub-username>/text2video-backend:latest
```

Then in Render, trigger a new deploy for the service.
