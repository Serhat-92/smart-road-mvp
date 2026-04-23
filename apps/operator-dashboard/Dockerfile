FROM node:20-alpine

WORKDIR /app/apps/operator-dashboard

COPY apps/operator-dashboard/package.json apps/operator-dashboard/package-lock.json ./
RUN npm ci

COPY apps/operator-dashboard /app/apps/operator-dashboard

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
