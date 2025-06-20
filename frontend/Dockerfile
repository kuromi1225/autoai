# Multi-stage build for optimized production image
FROM node:20-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install pnpm
RUN npm install -g pnpm

# Generate pnpm-lock.yaml if it doesn't exist
RUN if [ ! -f pnpm-lock.yaml ]; then pnpm install --lockfile-only; fi

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Production stage
FROM nginx:alpine as production

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

