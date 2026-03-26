# Multi-stage build for production
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend-react/package*.json ./
RUN npm ci
COPY frontend-react/ .
RUN npm run build

# Production stage
FROM python:3.11-slim AS backend

WORKDIR /app
COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy backend application
COPY backend/ .
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "main.prod.py"]
