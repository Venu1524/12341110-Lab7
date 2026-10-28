# ==============================================================================
# Service: web (Nginx Reverse Proxy & HTTP Gateway)
# Base Image: Nginx 1.27 Alpine (High performance, ultra-small ~25MB)
# ==============================================================================
FROM nginx:1.27-alpine

LABEL maintainer="Katari Venu (12341110)"
LABEL description="Nginx Reverse Proxy Gateway for Proximity Search API"
LABEL version="1.0.0"

# Remove default configuration and install custom configuration
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Expose HTTP port
EXPOSE 80

# Health check to ensure Nginx is responding
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1/nginx-health || exit 1

# Launch Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
