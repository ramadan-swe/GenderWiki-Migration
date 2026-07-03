# MW 1.35.5 → 1.39.17 Upgrade

## PHP
- Requires PHP ≥ 7.4.3.
- Additional PHP ext needed: `ext-calendar`.

## Dropped settings
Remove these from `LocalSettings.php`:
- `$wgEnableParserCache`
- `$wgCompiledFiles`
- `$wgSVGConverters`, `$wgSVGConverterPath`
- `$wgMaxImageArea`
- `$wgUseImageResize`

## Composer
MW 1.39 ships `composer.lock` inside `vendor/` instead of at MW root.
**After replacing core**: delete the old root-level `composer.lock`.

MW 1.39 pins `guzzlehttp/guzzle 7.4.5` and `symfony/yaml 5.4.23`, both flagged with
security advisories. Composer 2.10+ refuses to install them by default.
**Fix**: add `"policy": {"advisories": {"block": false}}` to the `config` section
of root `composer.json`.

## Extension compatibility

| Extension | Version / source | Notes |
|---|---|---|
| EmbedVideo | 2.8.0 (old GitLab repo) | New StarCitizenWiki repo (REL1_39) requires PHP ≥ 8.0. |
| Linter | REL1_39 | Required by DiscussionTools; absorbed into MW core from 1.40+. |
| VisualEditor | REL1_39 | Required by DiscussionTools. |
| DiscussionTools | REL1_39 | Requires Linter + VisualEditor + `$wgFragmentMode = [ 'html5', 'legacy' ]`. |
| Echo | REL1_39 | Notifications; needed by Flow→DT replacement. |
| RegexFun | REL1_39 | 4 templates use it; may need Scribunto migration for PHP 8.1+ later. |
| SemanticMediaWiki | 4.0.0 → 4.2.0 | Upgrade via Composer (`~4.2.0` in `composer.local.json`). Set `$smwgConfigFileDir` to a writable path. |
| Page Forms | Not installed | Provides `#arraymap` parser function used by some templates; install if needed. |

## Flow migration (prerequisite — must run on MW 1.35 first)

Flow boards must be converted to wikitext **before** upgrading MW,
because Flow is only functional on 1.35 and has no MW 1.39 compatible version.

1. Ensure the wiki is running MW 1.35 with Flow extension enabled.
2. From `flow-migration-scripts/`, run: `python3 dockerFullConvert.py batch`.
3. Verify conversion, then proceed with the MW upgrade below.

The conversion script was patched to emit `(ت ع م)` instead of `(UTC)`
in timestamps for DiscussionTools compatibility with Arabic locale.

See `flow-migration-scripts/README.md` for full details.

## Upgrade procedure

1. **Replace MW core** with `mediawiki-1.39.17.tar.gz` contents.
2. **Delete** the old root-level `composer.lock` (1.39 reads it from `vendor/`).
3. **Restore third-party extensions** using REL1_39 branches/tags.
4. **Review `composer.local.json`** — update extension version constraints if needed
   (e.g. `"mediawiki/semantic-media-wiki": "~4.2.0"` for SMW).
5. **Remove dropped settings** from `LocalSettings.php` (see above).
6. **Add `$wgFragmentMode = [ 'html5', 'legacy' ]`** (required by DiscussionTools).
7. **Symlink `www` → the new 1.39 codebase**, restart containers.
8. **Run `php maintenance/update.php --wiki=<db> --quick`**.
9. **Run `php maintenance/initSiteStats.php --wiki=<db> --update`**.
10. **Verify** via Special:Version.
