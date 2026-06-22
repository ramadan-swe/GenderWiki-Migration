# MediaWiki Docker Compose (local)

Quick notes to run the MediaWiki instance in this repo using Docker Compose.

## Services

- `docker-compose.yml` — defines services: `db` (MariaDB), `php-fpm`, `web` (Apache)
- `docker/php-fpm/Dockerfile` — PHP-FPM image, one per MW version
- `docker/apache/Dockerfile` + `docker/apache/apache.conf` — Apache (Ubuntu) with `proxy_fcgi` to PHP-FPM
- `docker/websecrets/genderiyya.xyz` — template secrets file mounted into the containers

## Versioned PHP Dockerfiles

| File | MW version | PHP version |
|---|---|---|
| `php-fpm/Dockerfile` | 1.35 / 1.39 | 7.4 |
| `php-fpm/Dockerfile-1.43` | 1.43 | 8.3 |

Switch the active Dockerfile in `docker-compose.yml` when upgrading:

```yaml
php-fpm:
  build:
    context: ./docker/php-fpm
    dockerfile: Dockerfile-1.43  # ← change per MW version
```

Before first run
1. Edit `docker/websecrets/genderiyya.xyz` and set the real database password and any other secrets. Example:

```php
<?php
$wgDBpassword = 'the_db_password_you_set_in_docker_compose';
$wgDBserver = 'db';
?>
```

2. Ensure the database password in `docker-compose.yml` matches the password you set in the secrets file (`MYSQL_PASSWORD`).

3. The compose file mounts `./www` as the webroot in the containers; the MediaWiki core lives at `./www/mw` so Apache is configured with an `Alias /mw` to keep `$wgScriptPath = '/mw'` working. The uploads directory is mounted from `./uploads` to `/srv/repositorea/genderiyya.xyz` — change these host paths if you want a different location.

Run the stack

```bash
docker compose build
docker compose up -d

# Watch logs (helpful during first boot / SQL import)
docker compose logs -f
```

Notes
- The SQL backup `genderiyya_wiki-20260303.sql` is mounted into the MariaDB init folder and will be imported automatically the first time MariaDB initializes its data directory. If you want to re-import, remove the volume `db_data` and restart.
- The site will be available at `http://localhost:8080/` (apache container ports are mapped to host 8080). Adjust ports in `docker-compose.yml` if needed.
- `www/LocalSettings.php` already includes `/srv/websecrets/genderiyya.xyz`; make sure that file defines `$wgDBpassword` (and optionally `$wgDBserver = 'db'`) to point to the MariaDB container.

If you want, I can update `www/LocalSettings.php` to set `$wgDBserver` automatically to `db` when running in Docker — tell me if you'd like that change.
