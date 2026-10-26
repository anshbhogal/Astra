# Stage 1: Build the optimized static production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for maximum layer cache reuse
COPY package*.json ./
RUN npm install

# Copy application source code and build production assets
COPY . .
RUN npm run build

# Stage 2: Production NGINX web server with SPA routing and compression
FROM nginx:1.27-alpine AS production

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom NGINX configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 3000
EXPOSE 3000

# Start NGINX in foreground
CMD ["nginx", "-g", "daemon off;"]
