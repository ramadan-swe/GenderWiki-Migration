# GenderWiki Migration

Local MediaWiki stack and tooling for migrating **Genderiyya wiki** (ويكي
الجندر) from Flow boards to wikitext, then upgrading MediaWiki across LTS
versions (1.35 → 1.39 → 1.43).

## Repo structure

| Path | What |
|---|---|
| [`docker/`](docker/README.md) | Docker Compose stack: MariaDB, PHP-FPM, Apache |
| [`flow-migration-scripts/`](flow-migration-scripts/README.md) | Python scripts to convert Flow boards to wikitext with full history |
| [`www/`](www/) | MediaWiki installation, config (`LocalSettings.php`, `Extensions.conf`, `Namespaces.conf`) |
| [`upgrade-notes/`](upgrade-notes/) | Step-by-step upgrade documentation per MW version |
| [`test/`](test/) | Extension downloader scripts for each MW version |
