# =============================================================================
# frontend/Dockerfile — Multi-stage build for the React + Vite application
#
# This Dockerfile uses a two-stage build pattern to keep the final image
# as small as possible:
#   Stage 1 (build):   Uses Node.js to install dependencies and compile the
#                      React app into optimised static files (HTML, JS, CSS).
#   Stage 2 (serve):   Copies only the compiled output into a lightweight
#                      Nginx image that serves the static files at runtime.
#                      Node.js is not present in the final image at all.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build
# Node 20 Alpine is used here — Alpine is a minimal Linux distro that
# significantly reduces image size while still providing all npm tooling.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# Copy package manifests first so Docker can cache the npm install layer.
# Subsequent builds will skip re-downloading packages if these files haven't changed.
COPY package*.json ./
RUN npm install

# Copy the rest of the source code and compile the production bundle.
# Output is written to /app/dist — a folder of plain static files.
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Serve
# We switch to a bare Nginx Alpine image (~40 MB). Nothing from the Node.js
# build stage is carried over except the compiled /app/dist output.
# ---------------------------------------------------------------------------
FROM nginx:alpine

# Copy the compiled static assets into Nginx's default web root.
COPY --from=build /app/dist /usr/share/nginx/html

# Replace the default Nginx config with our custom one.
# This config handles client-side routing (React Router) and proxies
# API requests to the backend service.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 — the standard HTTP port Nginx listens on.
EXPOSE 80

# Health check: verifies Nginx is up and serving the page.
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/ || exit 1
