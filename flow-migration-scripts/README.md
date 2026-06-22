# GenderWiki Flow Migration Scripts

Convert **Flow boards** to wikitext with full page history, then import the result
into a MediaWiki instance. Two entry points are provided:

| Script | Use case |
|---|---|
| `fullConvert.py` | Runs directly on the host (PHP + MySQL accessible on PATH) |
| `dockerFullConvert.py` | Runs inside a Docker Compose environment (uses `docker exec`) |

Both share `script.py` (the conversion script) and `settings.ini` (configuration).

---

## Prerequisites

- Python 3.10+ with `pymysql` and `requests` (install via `pip install -r requirements.txt`)
- A pywikibot installation (the scripts import `pywikibot`)
- Shell access to MediaWiki maintenance scripts (`createAndPromote.php`,
  `changePassword.php`, `resetUserEmail.php`, `importDump.php`, `nukeNS.php`,
  `initSiteStats.php`, `rebuildrecentchanges.php`)
- A bot/sysop wiki account — `FlowMigrationBot` is auto-created by the script
- Direct MySQL access to the wiki database
- `user-config.py` and `settings.ini`

---

## Setup

### 1. Pywikibot family file

Create `families/<family_name>_family.py` so pywikibot knows how to reach your
wiki. The family name must match `family` in `settings.ini` (`[pywikibot]`).

The easiest way is to use `pwb generate_family_file`:

```bash
pwb generate_family_file
# Insert URL to wiki: http://localhost:8080/wiki/
# Insert a short name (eg: freeciv): genderiyya
```

`pwb generate_family_file` auto-creates a `families/` directory in the same path as `user-config.py` and places the generated file there. Alternatively you can see the [pywikibot family docs](https://doc.wikimedia.org/pywikibot/stable/api_ref/family.html#module-family) and the [`generate_family_file` docs](https://doc.wikimedia.org/pywikibot/stable/utilities/scripts.html#generate-family-file-script).

### 2. Pywikibot user config

Create `user-config.py` in the same directory as the scripts:

```python
family = '<family_name>'
mylang = '<language_code>'
usernames['<family_name>']['<language_code>'] = 'FlowMigrationBot'
password_file = "user-passwords.py"
put_throttle = 0
```

The `password_file` setting tells pywikibot to read credentials from
`user-passwords.py` instead of prompting interactively.

### 3. Bot credentials

Copy `user-passwords.py.example` to `user-passwords.py` and edit:

```python
('<family_name>', 'FlowMigrationBot', '<your_strong_password>')
```

The tuple format is `(family, username, password)`. This file is read by both
pywikibot (during login) and the scripts themselves (when running
`createAndPromote`).

### 4. Settings file

Edit `settings.ini` to match your environment:

```ini
[pywikibot]
language = ar
family = <family_name>

[database]
host = 127.0.0.1
port = 3306
dbname = <wiki_database_name>
user = <db_user>
password = <db_password>
ssl_disabled = True

[api]
action = http://<host>:<port>/<wiki_path>/api.php
rest = http://<host>:<port>/<wiki_path>/rest.php/localhost/v3/transform/html/to/wikitext

[other]
# Docker-specific (only used by dockerFullConvert.py)
docker_db_container = <project>-db-1
docker_php_container = <project>-php-fpm-1
php_container_mw_path = /var/www/html/mw
# Non-Docker path (only used by fullConvert.py)
mw_dir_path = /path/to/mediawiki

[templates]
flow_present = {{فلو-ممكّن}}
lqt_present = {{ل-ك-ت-ممكّن}}
flow_past = {{مراجعة-فلو-قديمة}}
lqt_past = {{مراجعة-ل-ك-ت-قديمة}}
summary = {{ملخص-فلو|$summary}}
archivetop = {{بداية-أرشيف|حالة=مغلقة}}
archivetop_summary = {{بداية-أرشيف|ملخص=$summary|حالة=مغلقة}}
archivebottom = {{نهاية-أرشيف}}
```

| Section | Key | Description |
|---|---|---|
| `[pywikibot]` | `language` / `family` | Matches the family file and user-config.py |
| `[database]` | `host` / `port` / `dbname` / `user` / `password` | Direct MySQL connection credentials |
| `[api]` | `action` | Full URL to `api.php` |
| `[api]` | `rest` | Full URL to Parsoid's HTML→wikitext endpoint |
| `[other]` | `docker_*` / `mw_dir_path` | Docker container names and MW install paths |
| `[templates]` | `*` | Wikitext templates for marking converted pages |

---

## Usage

### Convert all Flow boards on a wiki

```bash
# With Docker
python dockerFullConvert.py batch

# Without Docker
python fullConvert.py batch
```

The script will:

1. Ensure the `FlowMigrationBot` account exists and is a sysop+bot
2. Confirm the bot's email (bypasses `$wgEmailConfirmToEdit`)
3. Set the bot's password hash directly via SQL (workaround for a
   `createAndPromote.php` bug)
4. Create marker templates (`قالب:فلو-ممكّن`, `قالب:ل-ك-ت-ممكّن`)
5. Query the database for all `flow-board` pages
6. For each board: export Flow topics via Parsoid REST API → convert to wikitext
   → delete the old Flow board page → import the XML dump containing full
   history
7. After all boards are processed: nuke NS 2600 (Topic namespace), run
   `initSiteStats.php`, and `rebuildrecentchanges.php`

You can restrict the range:

```bash
python dockerFullConvert.py batch 10 20   # boards 10 through 20
```

### Convert a single Flow board

```bash
python script.py "Talk:Page_name" out.xml "Talk:Page_name"
python importxml.py out.xml
```

---

 ## Post-conversion steps

The batch scripts handle nuking NS 2600, `initSiteStats.php`, and
`rebuildrecentchanges.php` automatically. After the script finishes:

1. **Disable the Flow extension** by removing (or commenting out)
   `wfLoadExtension('Flow')` and its config in your `LocalSettings.php`.

2. **Remove `$wgNamespaceContentModels`** lines that set `'flow-board'` in your
   namespace configuration (if any).

---

## File overview

| File | Purpose | Git |
|---|---|---|
| `script.py` | Conversion script (reads DB, calls Parsoid, builds XML) | committed |
| `fullConvert.py` | Non-Docker orchestrator (calls PHP/MySQL directly) | committed |
| `dockerFullConvert.py` | Docker orchestrator (routes commands via `docker exec`) | committed |
| `settings.ini` | All configuration (DB, API, templates, Docker container names) | committed |
| `user-config.py` | Pywikibot user configuration | committed |
| `user-passwords.py` | Bot credentials | **ignored** (copy from `.example`) |
| `user-passwords.py.example` | Template for credentials file | committed |
| `families/` | Pywikibot family files (one per wiki) | committed |
| `requirements.txt` | Python dependencies (`pymysql`, `requests`) | committed |

---
