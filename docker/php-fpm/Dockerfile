# MW 1.35 / 1.39 — PHP 7.4 (matches requirement ≥ 7.4.3)
# MW 1.43 → use Dockerfile-1.43 (PHP 8.3)
FROM php:7.4-fpm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libicu-dev libpng-dev libjpeg-dev libfreetype6-dev libzip-dev libxml2-dev zlib1g-dev libonig-dev git unzip ca-certificates \
    && docker-php-ext-configure intl \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) pdo_mysql mysqli mbstring xml intl gd zip opcache calendar \
    && pecl install apcu || true \
    && docker-php-ext-enable apcu || true \
    && mkdir -p /var/cache/wikido.xyz/genderiyya \
    && chown -R www-data:www-data /var/cache/wikido.xyz \
    && chmod -R 775 /var/cache/wikido.xyz \
    && rm -rf /var/lib/apt/lists/*

# Install Composer (copy from official Composer image)
COPY --from=composer/composer:2-bin /composer /usr/bin/composer
RUN composer --version

WORKDIR /var/www/html
