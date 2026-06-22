import re
import sys
import subprocess
import traceback
from pathlib import Path

import pywikibot
from pywikibot import Site

import script


class FlowMigrator:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print("Creating the one and only FlowMigrator instance...")            
            cls._instance = super().__new__(cls)
            cls._instance.config = script.get_config()
            # 1. First ensure the bot user exists on the wiki (before pywikibot login)
            cls._instance._create_and_promote_bot(cls._instance.config)
            # 2. Then initialize Pywikibot Site and login
            cls._instance.site = Site(*cls._instance.config["pywikibot"])
            cls._instance.site.login()
            # 3. Create marker templates once
            cls._instance._create_templates(cls._instance.config)

        return cls._instance

    @staticmethod
    def _get_password_from_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            import ast
            return ast.literal_eval(f.read().strip())[2]

    @staticmethod
    def _generate_mw_hash(password: str) -> str:
        import hashlib, base64, os
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac('sha512', password.encode(), salt, 30000, dklen=64)
        salt_b64 = base64.b64encode(salt).decode()
        dk_b64 = base64.b64encode(dk).decode()
        return f":pbkdf2:sha512:30000:64:{salt_b64}:{dk_b64}"

    def _create_and_promote_bot(self, config):
        database = config['dbconf']['database']
        db_user = config['dbconf']['user']
        db_password = config['dbconf']['password']
        PASSWORD_FILE_PATH = "user-passwords.py"

        try:
            bot_password = self._get_password_from_file(PASSWORD_FILE_PATH)
            print("Checking/Creating the FlowMigrationBot account via maintenance script...")

            # createAndPromote to create user and grant groups
            subprocess.run([
                "docker", "exec", "-u", "www-data", config['other']['docker_php_container'],
                "php", f"{config['other']['php_container_mw_path']}/maintenance/createAndPromote.php",
                f"--wiki={database}", "--force", "--bot", "--sysop",
                "FlowMigrationBot", bot_password
            ], check=True)

            print("Account verified/created and granted bot/sysop rights successfully!")

            # Set and confirm email
            subprocess.run([
                "docker", "exec", "-u", "www-data", config['other']['docker_php_container'],
                "php", f"{config['other']['php_container_mw_path']}/maintenance/resetUserEmail.php",
                f"--wiki={database}", "FlowMigrationBot", "bot@genderiyya.xyz"
            ], check=True)

            subprocess.run([
                "docker", "exec", config['other']['docker_db_container'],
                "mysql", "-u", f"{db_user}", f"-p{db_password}", database,
                "-e", "UPDATE user SET user_email_authenticated = DATE_FORMAT(NOW(), '%Y%m%d%H%i%s') WHERE user_name = 'FlowMigrationBot';"
            ], check=True)

            # Directly set the password hash via SQL, AFTER all
            # maintenance scripts (createAndPromote, resetUserEmail) are
            # done so none of them can overwrite it.
            mw_hash = self._generate_mw_hash(bot_password)
            subprocess.run([
                "docker", "exec", config['other']['docker_db_container'],
                "mysql", "-u", f"{db_user}", f"-p{db_password}", database,
                "-e", f"UPDATE user SET user_password = '{mw_hash}' WHERE user_name = 'FlowMigrationBot';"
            ], check=True)

        except subprocess.CalledProcessError as e:
            print(f"Server-side user setup failed: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error initializing user creation setup: {e}", file=sys.stderr)

    @staticmethod
    def _extract_template_name(raw: str) -> str | None:
        m = re.search(r'\{\{(.+?)\}\}', raw)
        return m.group(1) if m else None

    def _create_template(self, raw_name: str, content: str):
        name = self._extract_template_name(raw_name)
        if not name:
            print(f"Could not parse template name from '{raw_name}', skipping.")
            return
        title = f"قالب:{name}"
        page = pywikibot.Page(self.site, title)
        if page.exists():
            print(f"Template {title} already exists, skipping.")
            return
        page.text = content
        page.save(summary="إنشاء قالب لتحويل نقاشات فلو")
        print(f"Template {title} created.")

    def _create_templates(self, config):
        print("Creating marker templates if needed...")
        self._create_template(
            config["header_flow_present"],
            "<noinclude>\nهذا القالب يميز الصفحات التي تم تحويلها من فلو.\n</noinclude>"
        )
        self._create_template(
            config["header_lqt_present"],
            "<noinclude>\nهذا القالب يميز الصفحات التي تم تحويلها من ل-ك-ت.\n</noinclude>"
        )


def convert_all(skip: int = 0, end: int = 99999):
    conn = script.get_connection()
    cur = conn.cursor()
    cur.execute("""
                select page_namespace, page_title
                from page
                where page_content_model = 'flow-board'
                  and page_namespace != 2600""")

    # --- Integration: Instantiating the Singleton safely here ---
    migrator = FlowMigrator()
    site = migrator.site  # Safely reuses your logged-in Site instance
    config = migrator.config  # Safely reuses your configuration

    rows = cur.fetchall()
    if len(rows) > 0:
        print(f"{len(rows)} Flow boards found")
    if skip != 0 or end != 99999:
        input(f"Starting with {skip} and ending with {end}. Confirm?")
    processed = 0

    database = config['dbconf']['database']

    xml_path = Path(f"xml/{database}")
    xml_path.mkdir(parents=True, exist_ok=True)
    batch_mode = len(sys.argv) > 1 and sys.argv[1] == "batch"
    for ns, title in rows:
        processed += 1
        if processed < skip:
            continue
        if processed > end:
            break
        title = title.decode("utf8")
        cur.execute("""
                    SELECT COUNT(*)
                    FROM flow_topic_list ftl
                             JOIN flow_workflow fw
                                  ON ftl.topic_list_id = fw.workflow_id
                    WHERE fw.workflow_namespace = %s
                      AND BINARY fw.workflow_title_text = %s""", (ns, title))
        topic_count = cur.fetchone()[0]
        print(f"{title} has {topic_count} topics.")
        if topic_count >= 50:
            print("Too many topics to convert. Skipping.")
            continue
        if ns != 0:
            title = site.namespaces.resolve(ns)[0].canonical_prefix() + title
        if batch_mode:
            print(f"Exporting {title}.")
        else:
            input(f"Exporting {title}.")
        page = pywikibot.Page(site, title)
        # Now do the export
        try:
            out_path = Path(title.replace("/", "SLASH").replace(" ", "_") + ".xml")
            revs = script.convertBoard(title)
            script.finalize(revs)
            script.exportToXML(title, revs, out_path, title)
            assert out_path.exists()
            page.delete(reason="Delete flow board to make way for wikitext page history import", prompt=False)
            print("Importing XML to wiki...")

            # Pipe XML via stdin so file doesn't need to be inside the container
            with open(out_path, "rb") as xml_file:
                subprocess.run([
                    "docker", "exec", "-i", "-u", "www-data", config['other']['docker_php_container'],
                    "php", f"{config['other']['php_container_mw_path']}/maintenance/importDump.php",
                    f"--wiki={database}",
                    "--username-prefix=''"
                ], stdin=xml_file, check=True)
            out_path.rename(xml_path / out_path.name)
        except script.PageTooLarge:
            print(f"{title} too large to import, needs manual review", file=sys.stderr)
            if script.warnings:
                print("Extra warnings:", file=sys.stderr)
                for warning in script.warnings:
                    print(warning, file=sys.stderr)
            script.warnings = []
        except Exception:
            print(f"Error converting page {title}", file=sys.stderr)
            if script.warnings:
                print("Extra warnings:", file=sys.stderr)
                for warning in script.warnings:
                    print(warning, file=sys.stderr)
            traceback.print_exc()
    
    print("Nuking Flow Topic namespace data...")
    subprocess.run([
        "docker", "exec", "-u", "www-data", config['other']['docker_php_container'],
        "php", f"{config['other']['php_container_mw_path']}/maintenance/nukeNS.php",
        f"--wiki={database}", "--ns=2600", "--all", "--delete"
    ], check=True)

    print("Updating site statistics and recent changes...")
    subprocess.run([
        "docker", "exec", "-u", "www-data", config['other']['docker_php_container'],
        "php", f"{config['other']['php_container_mw_path']}/maintenance/initSiteStats.php",
        f"--wiki={database}", "--update"
    ], check=True)
    print("Site statistics and recent changes updated successfully.")
    
    print("Rebuilding recent changes...")
    subprocess.run([
        "docker", "exec", "-u", "www-data", config['other']['docker_php_container'],
        "php", f"{config['other']['php_container_mw_path']}/maintenance/rebuildrecentchanges.php",
        f"--wiki={database}"
    ], check=True)
    print("Recent changes rebuilt successfully. \nDone")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        convert_all(skip=int(sys.argv[2]), end=int(sys.argv[3]))
    else:
        convert_all()
