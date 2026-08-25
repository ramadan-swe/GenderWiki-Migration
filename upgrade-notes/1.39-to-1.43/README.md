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

## Extension versions: 1.39 → 1.43

Third-party extensions checked out in `test/extensions-1_43/` and copied into
`www-1.43/mw/extensions/` (without `.git`). The 1.39 column shows the branch/commit
from `test/extensions/`. Extensions not listed here are bundled with MW core at
the REL1_43 tag and require no separate download.

### Third-party extensions

| Extension | Repository | 1.39 (branch/commit) | 1.43 (branch/commit) | Notes |
|---|---|---|---|---|
| CLDR | [wikimedia/mediawiki-extensions-cldr](https://github.com/wikimedia/mediawiki-extensions-cldr.git) | `REL1_39` `65b782d` | `REL1_43` `2935d3d` | |
| ContactPage | [wikimedia/mediawiki-extensions-ContactPage](https://github.com/wikimedia/mediawiki-extensions-ContactPage.git) | `REL1_39` `e23cffc` | `REL1_43` `2964be3` | |
| Description2 | [wikimedia/mediawiki-extensions-Description2](https://github.com/wikimedia/mediawiki-extensions-Description2.git) | `REL1_39` `ed886d7` | `REL1_43` `c344916` | |
| Disambiguator | [wikimedia/mediawiki-extensions-Disambiguator](https://github.com/wikimedia/mediawiki-extensions-Disambiguator.git) | `REL1_39` `6cef18f` | `REL1_43` `eb81019` | |
| DismissableSiteNotice | [wikimedia/mediawiki-extensions-DismissableSiteNotice](https://github.com/wikimedia/mediawiki-extensions-DismissableSiteNotice.git) | `REL1_39` `1472645` | `REL1_43` `ae44ef6` | |
| EmbedVideo | [StarCitizenWiki/mediawiki-extensions-EmbedVideo](https://github.com/StarCitizenWiki/mediawiki-extensions-EmbedVideo.git) | `REL1_43` `86bbf18` | `REL1_43` `86bbf18` | |
| GetUserName | [Wikimedica/MediaWiki-extensions-GetUserName](https://github.com/Wikimedica/MediaWiki-extensions-GetUserName.git) | `v2.1` `68137cc` | `v2.1` `68137cc` | Same version; no MW-specific code. |
| InviteSignup | [wikimedia/mediawiki-extensions-InviteSignup](https://github.com/wikimedia/mediawiki-extensions-InviteSignup.git) | `REL1_39` `de58cc6` | `REL1_43` `010bb93` | |
| MassEditRegex | [wikimedia/mediawiki-extensions-MassEditRegex](https://github.com/wikimedia/mediawiki-extensions-MassEditRegex.git) | `REL1_39` `e5a8812` | `REL1_43` `79b640a` | |
| Matomo | [DaSchTour/matomo-mediawiki-extension](https://github.com/DaSchTour/matomo-mediawiki-extension.git) | `v5.0.0` `b74fca9` | `v5.0.0` `b74fca9` | Same version; no MW-specific code. |
| MetaMaster | [wikimedia/mediawiki-extensions-MetaMaster](https://github.com/wikimedia/mediawiki-extensions-MetaMaster.git) | `REL1_39` `f3df3f2` | `REL1_43` `6befe2b` | |
| MobileFrontend | [wikimedia/mediawiki-extensions-MobileFrontend](https://github.com/wikimedia/mediawiki-extensions-MobileFrontend.git) | `REL1_39` `2abb75a55` | `REL1_43` `65f905378` | |
| MyVariables | [wikimedia/mediawiki-extensions-MyVariables](https://github.com/wikimedia/mediawiki-extensions-MyVariables.git) | `REL1_39` `aa0e5c2` | `REL1_43` `4fed13d` | |
| NewestPages | [wikimedia/mediawiki-extensions-NewestPages](https://github.com/wikimedia/mediawiki-extensions-NewestPages.git) | `REL1_39` `076b892` | `REL1_43` `e0bfefe` | |
| OpenGraphMeta | [wikimedia/mediawiki-extensions-OpenGraphMeta](https://github.com/wikimedia/mediawiki-extensions-OpenGraphMeta.git) | `REL1_39` `6ac0c44` | `REL1_43` `fbc9c7b` | |
| PagedTiffHandler | [wikimedia/mediawiki-extensions-PagedTiffHandler](https://github.com/wikimedia/mediawiki-extensions-PagedTiffHandler.git) | `REL1_39` `711bd70` | `REL1_43` `b6e44d7` | |
| PageNotice | [wikimedia/mediawiki-extensions-PageNotice](https://github.com/wikimedia/mediawiki-extensions-PageNotice.git) | `REL1_39` `6a103be` | `REL1_43` `862d30f` | |
| RandomSelection | [wikimedia/mediawiki-extensions-RandomSelection](https://github.com/wikimedia/mediawiki-extensions-RandomSelection.git) | `REL1_39` `609924b` | `REL1_43` `cfa750c` | |
| RegexFun | [wikimedia/mediawiki-extensions-RegexFun](https://github.com/wikimedia/mediawiki-extensions-RegexFun.git) | `REL1_39` `51743ea` | `REL1_43` `64f4be7` | |
| RssFeed | [wikimedia/mediawiki-extensions-RSS](https://github.com/wikimedia/mediawiki-extensions-RSS.git) | `REL1_39` `2da8200` | `REL1_43` `aaf70e4` | |
| TemplateSandbox | [wikimedia/mediawiki-extensions-TemplateSandbox](https://github.com/wikimedia/mediawiki-extensions-TemplateSandbox.git) | `REL1_39` `fc11432` | `REL1_43` `ab47533` | |
| TimeMachine | [wikimedia/mediawiki-extensions-TimeMachine](https://github.com/wikimedia/mediawiki-extensions-TimeMachine.git) | `REL1_39` `b88685a` | `REL1_43` `0bbddbb` | |
| UserMerge | [gerrit.wikimedia.org/r/mediawiki/extensions/UserMerge](https://gerrit.wikimedia.org/r/mediawiki/extensions/UserMerge) | `REL1_39` `9e7ead3` | `REL1_43` `1aa2851` | |
| Variables | [wikimedia/mediawiki-extensions-Variables](https://github.com/wikimedia/mediawiki-extensions-Variables.git) | `REL1_39` `3efd415` | `REL1_43` `b9c1815` | |
| WikiLove | [wikimedia/mediawiki-extensions-WikiLove](https://github.com/wikimedia/mediawiki-extensions-WikiLove.git) | `REL1_39` `4a1319c` | `REL1_43` `86a38cf` | |

### Extensions dropped between 1.39 and 1.43

| Extension | 1.39 version | Reason |
|---|---|---|
| DiscussionTools | `REL1_39` `f6b06a03` | Merged into MW core in 1.40+. |
| Echo | `REL1_39` `8edd3eed` | Merged into MW core in 1.42+. |
| Flow | `REL1_39` `f611897b2` | Removed; boards already converted to wikitext. |
| Linter | `REL1_39` `82f32ce` | Merged into MW core in 1.40+. |

### Extensions added in 1.43

| Extension | 1.43 version | Reason |
|---|---|---|
| LoginNotify | bundled (MW core) | Ships with MW 1.43. |

### Skins

All skins (Vector, MonoBook, Timeless, MinervaNeue) ship with MW core. No separate downloads needed.
