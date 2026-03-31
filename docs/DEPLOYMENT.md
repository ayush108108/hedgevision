# Deployment Guide [Stage/Prod Level]

This guide covers deployment strategies for Staging and Production environments.

## Docker Containers

The application is containerized. The `backend` includes a `Dockerfile`.

### Building Backend Image
```bash
cd backend
docker build -t hedgevision-backend:latest .
```

### Running Backend Container
```bash
docker run -d \
  --name hedgevision-backend \
  -p 8000:8000 \
  -e SUPABASE_URL=... \
  -e SUPABASE_KEY=... \
  -e OPENAI_API_KEY=... \
  hedgevision-backend:latest
```

## Frontend Deployment

The frontend is a static site (SPA) that can be served by Nginx, Vercel, Netlify, or AWS S3+CloudFront.

### Building for Production
```bash
cd frontend-v2
npm run build
```
This produces a `dist/` folder containing the optimized static assets.

### Dockerizing Frontend (Nginx)
The `frontend-v2/Dockerfile` typically uses a multi-stage build to compile assets and serve them via Nginx.

```bash
cd frontend-v2
docker build -t hedgevision-frontend:latest .
```

## Staging vs. Production

It is recommended to have separate Supabase projects for Staging and Production to prevent data corruption.

| Env Var | Staging Value | Production Value |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://api-staging.yourdomain.com` | `https://api.yourdomain.com` |
| `SUPABASE_URL` | `https://staging-project.supabase.co` | `https://prod-project.supabase.co` |

## Infrastructure as Code (Optional)

If managing infrastructure via Terraform/Pulumi, ensure that the Postgres/TimescaleDB extensions are enabled on the managed database instance.

## CI/CD Pipeline (GitHub Actions)

Recommended workflow:
1.  **Push to `main`**: Triggers `test` + `build`.
2.  **Tag Release**: Triggers `build` + `push to registry` + `deploy to Staging`.
3.  **Manual Approval**: Promote Staging to Production.
