# MW 1.39 → 1.43 Upgrade Notes

This directory documents the upgrade from MediaWiki 1.39.17 to 1.43.8, including Semantic MediaWiki 4.2.0 → 5.0.2 → 6.0.1 and PHP 7.4 → 8.3.32.

## Overview

| Component | Before | After |
|---|---|---|
| MediaWiki | 1.39.17 | 1.43.8 |
| PHP | 7.4 (Dockerfile) | 8.3.32 (Dockerfile-1.43) |
| SMW | 4.2.0 | 5.0.2 → 6.0.1 |
| MariaDB | 10.11.14 | 10.11.14 (unchanged) |

## Step-by-Step

### Phase 1 — Backup

```bash
# Database
docker compose exec db mysqldump \
  -u root -prootPw0rd genderiyya_wiki \
  > backup-pre-1.43.sql

# Old install (rename to break symlink, serves as backup)
mv www-1.39 www-1.39.backup
```

### Phase 2 — Docker: PHP 8.3 image

```yaml
# docker-compose.yml — change build to use Dockerfile-1.43
php-fpm:
  build:
    context: ./docker/php-fpm
    dockerfile: Dockerfile-1.43
```

```bash
docker compose build php-fpm
```

### Phase 3 — Build new code directory

```bash
# Create layout
mkdir www-1.43

# Extract MW 1.43.8 core
tar xzf mediawiki-1.43.8.tar.gz \
  --strip-components=1 -C www-1.43/mw

# Copy configs from backup
cp www-1.39.backup/{LocalSettings.php,Extensions.conf,\
  Namespaces.conf,.php.ini,robots.txt} www-1.43/
cp -a www-1.39.backup/smw-config www-1.43/smw-config

# Copy pre-vetted extensions (overwrites bundled versions)
cp -a test/extensions-1_43/* www-1.43/mw/extensions/

# Create LocalSettings symlink
ln -sf ../LocalSettings.php www-1.43/mw/LocalSettings.php
```

**Before first composer run**, create `composer.local.json`:

```json
{
    "require": {
        "mediawiki/semantic-media-wiki": "~5.0.0"
    },
    "extra": {
        "merge-plugin": {
            "include": [
                "extensions/*/composer.json"
            ],
            "exclude": [
                "extensions/SemanticMediaWiki/composer.json"
            ]
        }
    }
}
```

> **Note:** SMW must be excluded from the merge-plugin to prevent duplicate autoload entries (see Issues below).

```bash
# Run composer (inside PHP 8.3 container after swap)
docker compose exec php-fpm \
  composer update --no-dev --optimize-autoloader \
  --working-dir=/var/www/html/mw
```

### Phase 4 — Symlink swap & restart

```bash
ln -sfn www-1.43 www
docker compose up -d
```

### Phase 5 — SMW 4.2 → 5.0 migration

```bash
docker compose exec php-fpm \
  php /var/www/html/mw/maintenance/update.php --quick
```

### Phase 6 — SMW 5.0 → 6.0 migration

```bash
# Update version constraint
# composer.local.json: "~5.0.0" → "~6.0.0"

docker compose exec php-fpm \
  composer update --no-dev --optimize-autoloader \
  --working-dir=/var/www/html/mw

docker compose exec php-fpm \
  php /var/www/html/mw/maintenance/update.php --quick
```

### Phase 7 — Finalize

```bash
docker compose exec php-fpm \
  php /var/www/html/mw/maintenance/runJobs.php
docker compose exec php-fpm \
  php /var/www/html/mw/maintenance/initSiteStats.php --update
docker compose exec php-fpm \
  php /var/www/html/mw/maintenance/rebuildrecentchanges.php
```

## Issues & Fixes

### 1. SMW → merge-plugin autoload duplicates

**Cause:** SMW is installed by `composer/installers` into `extensions/SemanticMediaWiki/`. The merge-plugin includes `extensions/*/composer.json`, which picks up SMW's autoload `files` entry (`includes/GlobalFunctions.php`). After two `composer update` runs (one per SMW version step), duplicate entries accumulated in both `autoload_files.php` and `autoload_static.php` with different hash keys, causing:

```
Fatal error: Cannot redeclare smwfContLang()...
```

**Fix — permanent:** Add `"exclude": ["extensions/SemanticMediaWiki/composer.json"]` to the merge-plugin config. SMW's autoloading is fully handled by the normal Composer install path.

**Fix — immediate (if already broken):** Remove duplicate entries from:

- `vendor/composer/autoload_files.php`
- `vendor/composer/autoload_static.php`

### 2. Renameuser referenced but archived

`Extensions.conf` contained `wfLoadExtension('Renameuser')`. This extension was merged into MW core in 1.40 and archived. Remove this line before running `update.php` on MW 1.43.

### 3. `smw-config/` location

`LocalSettings.php` references `$smwgConfigFileDir = "$IP/../smw-config"`, placing it at the wiki root level (`www-1.43/smw-config/`). Ensure this directory is copied alongside `LocalSettings.php`, not inside `mw/`.

### 4. PHP 8.3 required for SMW ≥ 5.x

SMW 5.x and 6.x both require PHP ≥ 8.1. Since MW 1.39 runs PHP 7.4, the SMW upgrade **cannot** happen before the MW core swap. Sequence: build PHP 8.3 image → install MW 1.43 + SMW 5.0 → `update.php` → SMW 6.0 → `update.php`.

## Shelf Notes

| Extension | Action | Reason |
|---|---|---|
| Renameuser | Remove from Extensions.conf | Archived; merged into MW 1.40 core |
| LocalisationUpdate | Remove from Extensions.conf | Archived; use `php run.php rebuildtranslationcache` if needed |
| ParserHooks | Composer dependency of SMW | Handled automatically by `composer update` |
