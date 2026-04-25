FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/operator-dashboard/package.json apps/operator-dashboard/package-lock.json ./
RUN npm ci

COPY apps/operator-dashboard/ ./

ARG VITE_API_BASE_URL=http://127.0.0.1:8080
ARG VITE_USE_MOCK_API=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USE_MOCK_API=$VITE_USE_MOCK_API

RUN npm run build

FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
