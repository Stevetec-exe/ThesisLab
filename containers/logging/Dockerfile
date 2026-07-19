# Build stage
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy sources and compile
COPY tsconfig.json ./
COPY src ./src

RUN npm run build

# Runtime stage
FROM node:22-alpine

WORKDIR /app

# Install only production dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy compiled JavaScript
COPY --from=build /app/dist ./dist

COPY config ./config
# Start the worker
CMD ["node", "dist/index.js"]