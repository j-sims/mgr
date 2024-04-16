# Use the Nginx image
FROM nginx:latest

# Remove default NGINX configuration files
RUN rm /etc/nginx/conf.d/default.conf

# Generate a self-signed SSL certificate
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl.key -out /etc/nginx/ssl.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

RUN apt update && apt install -y apache2-utils && apt clean

# Expose port 80 and 443 (HTTP and HTTPS)
EXPOSE 80
#EXPOSE 443 #disabled due to powerbi limitations

ADD run.sh /run.sh
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://127.0.0.1/health 

# Start NGINX
CMD ["bash", "/run.sh"]