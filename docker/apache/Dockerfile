FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends apache2 imagemagick ca-certificates \
    && a2enmod proxy proxy_fcgi rewrite headers env setenvif \
    && mkdir -p /var/cache/wikido.xyz/genderiyya \
    && chown -R www-data:www-data /var/cache/wikido.xyz \
    && chmod -R 775 /var/cache/wikido.xyz \
    && rm -rf /var/lib/apt/lists/*

COPY apache.conf /etc/apache2/sites-available/000-default.conf

RUN mkdir -p /var/www/html && chown -R www-data:www-data /var/www/html

EXPOSE 80

CMD ["apache2ctl", "-D", "FOREGROUND"]
