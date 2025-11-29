FROM nginx:1.24-alpine

RUN apk add --no-cache curl

RUN rm -rf /etc/nginx/conf.d/*

COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
