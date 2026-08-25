# Flow-to-Wikitext Migration: Parsoid Configuration

## Problem

The `flow-migration-scripts/dockerFullConvert.py` script fails with:

```
Flow\Exception\WikitextException: Conversion from 'html' to 'wikitext' was requested,
but core's Parser only supports 'wikitext' to 'html' conversion
```

This happens when the script calls the Flow API with `vthformat=wikitext` (or `vphformat=wikitext`), which requires converting Flow's internally-stored HTML content back to wikitext. The conversion is supposed to be handled by Parsoid/PHP, but it's not available.

## Root Cause

MediaWiki 1.35.5 ships Parsoid/PHP as a bundled composer library (`vendor/wikimedia/parsoid`). VisualEditor auto-configures and uses it with zero setup. However, **Flow does not use VisualEditor's auto-configuration**. Flow's conversion code (`extensions/Flow/includes/Conversion/Utils.php`) independently checks `$wgVirtualRestConfig['modules']['parsoid']` to find a Parsoid instance. On a default MW 1.35.5 installation where Parsoid was never explicitly loaded, this config is empty.

The fallback path (`Utils::parser()`) only supports wikitext-to-HTML, not the reverse. Hence the error.

Production (`genderiyya.xyz`) has the same issue — Parsoid was never loaded there either, which is why the migration script originally failed on production.

## Solution

Two things are needed:

1. **Explicitly load the Parsoid extension** so its REST routes are registered at `rest.php`.
2. **Point `$wgVirtualRestConfig`** at the Parsoid REST endpoint.

### With Docker (Docker Compose setup)

In `LocalSettings.php` or an included config file (e.g. `Extensions.conf`):

```php
// Load the bundled Parsoid extension (not auto-loaded in 1.35.5)
wfLoadExtension( 'Parsoid', "$IP/vendor/wikimedia/parsoid/extension.json" );

// Tell Flow where to find the Parsoid REST endpoint
$wgVirtualRestConfig['modules']['parsoid'] = [
    'url' => 'http://web/mw/rest.php',  // Docker service name for Apache
    'domain' => 'localhost',
];
```

The `url` must point to `rest.php` reachable from the PHP-FPM container. In Docker Compose this is the Apache container's service name (`web`), not `localhost`, because PHP-FPM and Apache run in separate containers.

### Without Docker (bare-metal / VM)

In `LocalSettings.php`:

```php
wfLoadExtension( 'Parsoid', "$IP/vendor/wikimedia/parsoid/extension.json" );
```

No `$wgVirtualRestConfig` override is needed — the default URL resolves to `rest.php` on the same server, which works when everything runs on one host.

### Apache/nginx URL rewriting

If you use `mod_rewrite` for short URLs, ensure `rest.php` is **not** rewritten to `index.php`. The Parsoid REST endpoint is at `rest.php/{domain}/v3/...` and must reach the PHP handler directly. Example for Apache:

```apache
RewriteCond %{HTTP_USER_AGENT} !^(VisualEditor)
RewriteCond %{DOCUMENT_ROOT}%{REQUEST_URI} !-f
RewriteCond %{DOCUMENT_ROOT}%{REQUEST_URI} !-d
RewriteRule ^(.*)$ %{DOCUMENT_ROOT}/wiki/index.php [L]
```

## Verification

After applying the fix, restart PHP-FPM, then test:

```bash
curl -s --get "http://localhost:8080/mw/api.php" \
  --data-urlencode "action=flow" \
  --data-urlencode "submodule=view-topic-history" \
  --data-urlencode "page=Topic:<workflow-uuid>" \
  --data-urlencode "vthformat=wikitext" \
  --data-urlencode "format=json" | python3 -m json.tool
```

A successful response returns `flow.view-topic-history.result.topic.revisions` with wikitext content. A failure returns `error.internal_api_error_Flow\Exception\WikitextException`.

## Component Summary

| Component | Version | Notes |
|---|---|---|
| MediaWiki | 1.35.5 | LTS, PHP 8.3.6 (not officially supported but works) |
| Parsoid/PHP | 0.12.1 (bundled) | Composer lib `wikimedia/parsoid`, must be loaded explicitly |
| Flow | REL1_35-7062bfa | Extension, requires Parsoid for HTML↔wikitext |
| VisualEditor | bundled | Auto-configures Parsoid for VE, but Flow doesn't use VE's config |
