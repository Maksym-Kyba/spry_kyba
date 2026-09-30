FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG COGNITO_USER_POOL_ID COGNITO_CLIENT_ID COGNITO_DOMAIN COGNITO_GOOGLE_ENABLED
RUN COGNITO_USER_POOL_ID="$COGNITO_USER_POOL_ID" COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
    COGNITO_DOMAIN="$COGNITO_DOMAIN" COGNITO_GOOGLE_ENABLED="$COGNITO_GOOGLE_ENABLED" \
    npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
