FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY app ./app
COPY next.config.mjs .
ARG NEXT_PUBLIC_MAPBOX_TOKEN
ARG BACKEND_URL=http://backend:5000
ENV NEXT_PUBLIC_MAPBOX_TOKEN=$NEXT_PUBLIC_MAPBOX_TOKEN
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
