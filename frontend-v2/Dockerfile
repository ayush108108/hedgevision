# syntax=docker/dockerfile:1

# ==============================================================================
# HedgeVision Frontend — Multi-stage Production Build
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependencies — cache npm ci separately from source
# ------------------------------------------------------------------------------
FROM node:20-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps --include=dev

# ------------------------------------------------------------------------------
# Stage 2: Builder — compile Vite bundle with build-time env vars
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time arguments (Vite bakes these into the bundle)
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_BASE_PATH=/
ARG VITE_SUPABASE_URL=
ARG VITE_SUPABASE_ANON_KEY=
ARG VITE_FEATURE_PORTFOLIO=false
ARG VITE_FEATURE_NEWS=false
ARG VITE_FEATURE_CALCULATOR=false
ARG VITE_FEATURE_WATCHLIST=false
ARG VITE_FEATURE_BACKTEST=false
ARG VITE_FEATURE_ONBOARDING=false
ARG VITE_FEATURE_AUTH=false

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_BASE_PATH=$VITE_BASE_PATH \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
    VITE_FEATURE_PORTFOLIO=$VITE_FEATURE_PORTFOLIO \
    VITE_FEATURE_NEWS=$VITE_FEATURE_NEWS \
    VITE_FEATURE_CALCULATOR=$VITE_FEATURE_CALCULATOR \
    VITE_FEATURE_WATCHLIST=$VITE_FEATURE_WATCHLIST \
    VITE_FEATURE_BACKTEST=$VITE_FEATURE_BACKTEST \
    VITE_FEATURE_ONBOARDING=$VITE_FEATURE_ONBOARDING \
    VITE_FEATURE_AUTH=$VITE_FEATURE_AUTH

RUN npm run build

# ------------------------------------------------------------------------------
# Stage 3: Runtime — production nginx serving static assets
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root nginx
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-qO-", "http://localhost:80/"]

CMD ["nginx", "-g", "daemon off;"]
