# --- STAGE 1: Build the Angular Application ---
FROM node:24-alpine AS build

# Set the working directory inside the container
WORKDIR /app

# Copy package descriptors first to take advantage of Docker caching layers
COPY package.json package-lock.json ./

# Install project dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the project for production 
# Note: Output goes into the dist/ directory
RUN npm run build -- --configuration=production

# --- STAGE 2: Serve the App using Nginx ---
FROM nginx:alpine

# Copy the custom Nginx configuration file
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets from the build stage to Nginx's HTML root directory
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Expose port 80 to the outside world
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
