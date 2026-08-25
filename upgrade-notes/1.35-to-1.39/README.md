# MW 1.35.5 → 1.39.17 Upgrade

## PHP
- Requires PHP ≥ 7.4.3.
- Additional PHP ext needed: `ext-calendar`.

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
| DiscussionTools | REL1_39 | Requires Linter + VisualEditor. |
| Echo | REL1_39 | Notifications; needed by Flow→DT replacement. |
| RegexFun | REL1_39 | 4 templates use it; may need Scribunto migration for PHP 8.1+ later. |
| SemanticMediaWiki | 4.0.0 → 4.2.0 | Upgrade via Composer (`~4.2.0` in `composer.local.json`).|
| Page Forms | Not installed | Provides `#arraymap` parser function used by some templates and pages; install if needed. |

## Extension versions: 1.39

Third-party extensions checked out in `test/extensions/` and copied into
`www-moved-1.39.backup/mw/extensions/` (without `.git`). Extensions not listed
here are bundled with MW core at the REL1_39 tag and require no separate download.

### Third-party extensions

| Extension | Repository | Branch/Tag | Commit | Notes |
|---|---|---|---|---|
| CLDR | [wikimedia/mediawiki-extensions-cldr](https://github.com/wikimedia/mediawiki-extensions-cldr.git) | `REL1_39` | `65b782d` | |
| ContactPage | [wikimedia/mediawiki-extensions-ContactPage](https://github.com/wikimedia/mediawiki-extensions-ContactPage.git) | `REL1_39` | `e23cffc` | |
| Description2 | [wikimedia/mediawiki-extensions-Description2](https://github.com/wikimedia/mediawiki-extensions-Description2.git) | `REL1_39` | `ed886d7` | |
| Disambiguator | [wikimedia/mediawiki-extensions-Disambiguator](https://github.com/wikimedia/mediawiki-extensions-Disambiguator.git) | `REL1_39` | `6cef18f` | |
| DismissableSiteNotice | [wikimedia/mediawiki-extensions-DismissableSiteNotice](https://github.com/wikimedia/mediawiki-extensions-DismissableSiteNotice.git) | `REL1_39` | `1472645` | |
| DiscussionTools | [wikimedia/mediawiki-extensions-DiscussionTools](https://github.com/wikimedia/mediawiki-extensions-DiscussionTools.git) | `REL1_39` | `f6b06a03` | New in 1.39; requires Linter + VisualEditor. |
| Echo | [gerrit.wikimedia.org/r/mediawiki/extensions/Echo](https://gerrit.wikimedia.org/r/mediawiki/extensions/Echo) | `REL1_39` | `8edd3eed` | |
| EmbedVideo | [StarCitizenWiki/mediawiki-extensions-EmbedVideo](https://github.com/StarCitizenWiki/mediawiki-extensions-EmbedVideo.git) | `v4.1.0` | `6982ef6` | Downloaded as `mediawiki-extensions-EmbedVideo`, copied as `EmbedVideo`. Production kept old v2.8.0. |
| Flow | [wikimedia/mediawiki-extensions-Flow](https://github.com/wikimedia/mediawiki-extensions-Flow.git) | `REL1_39` | `f611897b2` | Removed after Flow→wikitext conversion. |
| GetUserName | [Wikimedica/MediaWiki-extensions-GetUserName](https://github.com/Wikimedica/MediaWiki-extensions-GetUserName.git) | `v2.1` | `68137cc` | |
| InviteSignup | [wikimedia/mediawiki-extensions-InviteSignup](https://github.com/wikimedia/mediawiki-extensions-InviteSignup.git) | `REL1_39` | `de58cc6` | |
| Linter | [wikimedia/mediawiki-extensions-Linter](https://github.com/wikimedia/mediawiki-extensions-Linter.git) | `REL1_39` | `82f32ce` | New in 1.39; absorbed into MW core from 1.40+. |
| MassEditRegex | [wikimedia/mediawiki-extensions-MassEditRegex](https://github.com/wikimedia/mediawiki-extensions-MassEditRegex.git) | `REL1_39` | `e5a8812` | |
| Matomo | [DaSchTour/matomo-mediawiki-extension](https://github.com/DaSchTour/matomo-mediawiki-extension.git) | `v5.0.0` | `b74fca9` | |
| MetaMaster | [wikimedia/mediawiki-extensions-MetaMaster](https://github.com/wikimedia/mediawiki-extensions-MetaMaster.git) | `REL1_39` | `f3df3f2` | |
| MobileFrontend | [wikimedia/mediawiki-extensions-MobileFrontend](https://github.com/wikimedia/mediawiki-extensions-MobileFrontend.git) | `REL1_39` | `2abb75a55` | |
| MyVariables | [wikimedia/mediawiki-extensions-MyVariables](https://github.com/wikimedia/mediawiki-extensions-MyVariables.git) | `REL1_39` | `aa0e5c2` | |
| NewestPages | [wikimedia/mediawiki-extensions-NewestPages](https://github.com/wikimedia/mediawiki-extensions-NewestPages.git) | `REL1_39` | `076b892` | |
| OpenGraphMeta | [wikimedia/mediawiki-extensions-OpenGraphMeta](https://github.com/wikimedia/mediawiki-extensions-OpenGraphMeta.git) | `REL1_39` | `6ac0c44` | |
| PagedTiffHandler | [wikimedia/mediawiki-extensions-PagedTiffHandler](https://github.com/wikimedia/mediawiki-extensions-PagedTiffHandler.git) | `REL1_39` | `711bd70` | |
| PageNotice | [wikimedia/mediawiki-extensions-PageNotice](https://github.com/wikimedia/mediawiki-extensions-PageNotice.git) | `REL1_39` | `6a103be` | |
| RandomSelection | [wikimedia/mediawiki-extensions-RandomSelection](https://github.com/wikimedia/mediawiki-extensions-RandomSelection.git) | `REL1_39` | `609924b` | |
| RegexFun | [wikimedia/mediawiki-extensions-RegexFun](https://github.com/wikimedia/mediawiki-extensions-RegexFun.git) | `REL1_39` | `51743ea` | |
| RssFeed | [wikimedia/mediawiki-extensions-RSS](https://github.com/wikimedia/mediawiki-extensions-RSS.git) | `REL1_39` | `2da8200` | |
| TemplateSandbox | [wikimedia/mediawiki-extensions-TemplateSandbox](https://github.com/wikimedia/mediawiki-extensions-TemplateSandbox.git) | `REL1_39` | `fc11432` | |
| Thanks | [wikimedia/mediawiki-extensions-Thanks](https://github.com/wikimedia/mediawiki-extensions-Thanks.git) | `REL1_39` | `e693b7bd` | |
| TimeMachine | [wikimedia/mediawiki-extensions-TimeMachine](https://github.com/wikimedia/mediawiki-extensions-TimeMachine.git) | `REL1_39` | `b88685a` | |
| UserMerge | [gerrit.wikimedia.org/r/mediawiki/extensions/UserMerge](https://gerrit.wikimedia.org/r/mediawiki/extensions/UserMerge) | `REL1_39` | `9e7ead3` | |
| Variables | [wikimedia/mediawiki-extensions-Variables](https://github.com/wikimedia/mediawiki-extensions-Variables.git) | `REL1_39` | `3efd415` | |
| WikiLove | [wikimedia/mediawiki-extensions-WikiLove](https://github.com/wikimedia/mediawiki-extensions-WikiLove.git) | `REL1_39` | `4a1319c` | |

### Extensions not downloaded (MW core bundled)

These are part of the MW 1.39 tarball and don't need separate installation:

AbuseFilter, CategoryTree, Cite, CiteThisPage, CodeEditor, ConfirmEdit,
Gadgets, ImageMap, InputBox, Interwiki, Math, MultimediaViewer, Nuke,
OATHAuth, PageImages, ParserFunctions, PdfHandler, Poem, ReplaceText,
Scribunto, SecureLinkFixer, SemanticMediaWiki (installed via Composer),
SpamBlacklist, SyntaxHighlight_GeSHi, TemplateData, TextExtracts,
TitleBlacklist, VisualEditor, WikiEditor.

### Extensions removed before 1.39

| Extension | Reason |
|---|---|
| LocalisationUpdate | Archived; use `php run.php rebuildtranslationcache`. |
| ParserHooks | SMW composer dependency; handled automatically. |
| Renameuser | Merged into MW core in 1.40 (removed before 1.39). |

### Skins

All skins (Vector, MonoBook, Timeless, MinervaNeue) ship with MW core. No separate downloads needed.

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
5. **Symlink `www` → the new 1.39 codebase**, restart containers.
6. **Run `php maintenance/update.php --wiki=<db> --quick`**.
7. **Run `php maintenance/initSiteStats.php --wiki=<db> --update`**.
8. **Verify** via Special:Version.
