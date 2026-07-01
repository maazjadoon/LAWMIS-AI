# Step 1: Build React static assets
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency configs
COPY package*.json ./

# Install packages
RUN npm ci

# Copy sources
COPY . .

# Set VITE_API_BASE_URL to empty/relative path
# Nginx proxy will handle routing requests to backend
ENV VITE_API_BASE_URL=""

# Build production distribution
RUN npm run build

# Step 2: Serve React distribution using Nginx proxy
FROM nginx:1.25-alpine

# Copy built distribution from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx routing profile
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
