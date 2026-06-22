import configparser
import functools
import re
import ipaddress
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pymysql
import requests
import traceback

from pywikibot import Site
from pywikibot.comms import http


@functools.cache
def get_config():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    return {
        "dbconf": {
            "host": config.get("database", "host", fallback="localhost"),
            "user": config.get("database", "user", fallback="mediawiki"),
            "port": int(config.get("database", "port", fallback="3306")),
            "password": config.get("database", "password", fallback=""),
            "read_default_file": config.get(
                "database", "read_default_file", fallback="~/.my.cnf"
            ),
            "database": config.get("database", "dbname", fallback="testwiki"),
            "ssl_disabled": config.getboolean(
                "database", "ssl_disabled", fallback=False
            ),
        },
        "pywikibot": [
            config.get("pywikibot", "language", fallback="mediawiki"),
            config.get("pywikibot", "family", fallback="mediawiki"),
        ],
        "actionapi": config.get(
            "api", "action", fallback="https://www.mediawiki.org/w/api.php"
        ),
        "restapi": config.get(
            "api",
            "rest",
            fallback="https://www.mediawiki.org/api/rest_v1/transform/html/to/wikitext",
        ),
        "straight_from_lqt": config.get("mode", "straight_from_lqt", fallback=False),
        "header_flow_present": config.get(
            "templates", "flow_present", fallback="{{Flow-enabled}}"
        )
        + "\n\n",
        "header_flow_past": config.get(
            "templates", "flow_past", fallback="{{Flow imported revision}}"
        )
        + "\n\n",
        "header_lqt_present": config.get(
            "templates", "lqt_present", fallback="{{LQT-enabled}}"
        ),
        "header_lqt_past": config.get(
            "templates", "lqt_past", fallback="{{LiquidThreads imported revision}}"
        ),
        "summary_template": config.get(
            "templates", "summary", fallback="{{Flow summary|$summary}}"
        ),
        "archivetop_template": config.get(
            "templates", "archivetop", fallback="{{Archive top|status=resolved}}"
        ),
        "archivetop_summary_template": config.get(
            "templates",
            "archivetop_summary",
            fallback="{{Archive top|summary=$summary|status=resolved}}",
        ),
        "archivebottom_template": config.get(
            "templates", "archivebottom", fallback="{{Archive bottom}}"
        ),
        "skip_lqt_early_warning": config.get(
            "suppresswarnings", "lqt_early", fallback=False
        ),
        "other": {
            "docker_db_container": config.get(
                "other", "docker_db_container", fallback="genderwiki-migration-db-1"
            ),
            "docker_php_container": config.get(
                "other", "docker_php_container",
                fallback="genderwiki-migration-php-fpm-1"
            ),
            "php_container_mw_path": config.get(
                "other", "php_container_mw_path", fallback="/var/www/html/mw"
            ),
            "mw_dir_path": config.get(
                "other", "mw_dir_path", fallback="/var/www/html/mw"
            ),
        },
    }


@functools.cache
def get_connection():
    return pymysql.connect(**get_config()["dbconf"])


session = requests.Session()
warnings = []
USER_AGENT = {
    "User-Agent": "Genderiyya maintenance script (adapted from https://gitlab.wikimedia.org/pppery/flow-export-with-history)"
}
_session_initialized = False


def _init_session():
    global _session_initialized
    if _session_initialized:
        return
    site = Site()
    site.login()
    session.cookies = http.cookie_jar
    _session_initialized = True


def apicall(params: dict, *keys):
    _init_session()
    json = session.get(
        url=get_config()["actionapi"], params=params, headers=USER_AGENT
    ).json()
    for key in keys:
        if key not in json:
            raise RuntimeError(
                f"API call failed to return required key {key}: returned {json} instead"
            )
        json = json[key]
    return json


def html2wt(html: str, title: str):
    _init_session()
    return session.post(
        url=get_config()["restapi"],
        json={"html": html, "title": title},
        headers=USER_AGENT,
    ).text


@functools.cache
def get_header_revs(title: str):
    """Convert the header of a Flow board to a set of wikitextified revisions. Includes any revisions from /LQT Archive 1 if needed"""
    flow_header_params = {
        "action": "flow",
        "submodule": "view-header",
        "page": title,
        "format": "json",
        "vhformat": "wikitext",
    }
    revs = []
    lqt_pages = []
    conf = get_config()
    straight_from_lqt = conf["straight_from_lqt"]
    # In case no header revs exist
    content = ""
    while True:
        headerData = apicall(flow_header_params, "flow", "view-header", "result")

        try:
            revision = headerData["header"]["revision"]
            revid = revision["revisionId"]
        except KeyError:
            # We're at the end of the revision list
            break
        revs.append(revision)
        content = revision["content"]["content"]
        if revision["content"]["format"] != "wikitext":
            if not straight_from_lqt:
                # Flow header API can only return HTML here so decode it
                content = html2wt(content, title)
            # For straight_from_lqt mode there are only two header revs
            # and we don't need to try to decode the second one
            # since it has basically the same content as the first one
            # and will be deleted anyway. This means we don't need a REST API connection
        if content == "" or content[0] != "\n":
            content = "\n" + content
        content = conf["header_flow_past"] + content
        # Delete the LQT archive header entirely. Is this a good idea?
        # And maintain a list of possible LQT Archive 1 pages to handle later
        pat = r"\{\{LQT page converted to Flow\|archive=([^|]*)\|[^}]*\}\}"
        lqt_match = re.search(pat, content)
        if lqt_match:
            if lqt_match[1] == "Project:Support_desk/old":
                # This wrong old page was added to the history, exclude it
                pass
            elif lqt_match[1] not in lqt_pages:
                lqt_pages.append(lqt_match[1])
            content = re.sub(pat, "", content)
        revision["content"]["content"] = content
        # Add an edit summary for later and move on the next revision
        prev = revision["previousRevisionId"]
        revision["editsummary"] = "Edited header"
        if not prev:
            break
        flow_header_params["vhrevId"] = prev
    if lqt_pages:
        # Ultimate failsafe in case something odd happened - where it would have put it
        if "/Flow" in title:
            lqt_pages.append(title.replace("/Flow", "/LQT Archive 1"))
        # Now add those revisions too
        newrevs, default = mungeLqtArchive(lqt_pages, content)
        # Delete the last revision ("Flow talk page manager edited the description")
        # which adds a {{Archive for converted LQT page}} wrapper; we don'tcare
        del revs[-1]
        if straight_from_lqt:
            # Delete the second-to-last revision ("Flow talk page manager created the description")
            # which shows the current version of the description imported; we don't care either
            # any header changes as a result of Parsoid roundtripping without enough seler
            # will end up not ever making their way into the export then, which is fine
            del revs[-1]
            # Then there shouldn't be anything else in the revs list either, unless someone did something
            # that they shouldn't
            assert not revs
        else:
            # Leave the second-to-last (now last) revision as a marker for the convert
            # which occasionally garbles some stuff because LQT and Flow aren't quite compatible
            revs[-1]["editsummary"] = "Converted LQT to Flow"
            revs[-1]["content"]["content"] = revs[-1]["content"]["content"].replace(
                "{{#UseLiquidThreads:1}}", ""
            )
            revs[-1]["content"]["content"] = revs[-1]["content"]["content"].replace(
                "{{#useliquidthreads:1}}", ""
            )
        revs.extend(newrevs)
    elif straight_from_lqt:
        raise RuntimeError("LQT Archive not found")
    else:
        default = conf["header_flow_past"] + content
    return revs, default


def convertHeader(title: str, year: int | None = None):
    revs, default = get_header_revs(title)
    # Return revisions oldest-first because that's how MediaWiki import expects them to be ordered
    if year:
        newRevs = []
        lastContent = ""
        # The attribution history of the header gets garbled a bit here. There's no way around that
        # with this paradigm
        # Likewise for LQT if comments are made in the header (which people did for some reason)
        # they get duplicated across all years
        for rev in revs[::-1]:
            ryear = int(rev["timestamp"][: len(str(year))])
            if ryear < year:
                lastContent = rev["content"]["content"]
            elif ryear == year:
                newRevs.append(rev)
            else:
                break
        if not newRevs and not lastContent:
            conf = get_config()
            realyear = str(year)[:4]
            if realyear <= "2015" or conf["straight_from_lqt"]:
                lastContent = conf["header_lqt_past"]
            else:
                lastContent = conf["header_flow_past"]
        return newRevs, lastContent + "\n"
    return revs[::-1], default


def exportToXML(
    title: str, revs: list, outfile: str | Path = "out.xml", outtitle: str | None = None
):
    _init_session()
    """Convert the given Flow API-style JSON revisions to XML that can be imported into MediaWiki

    All revision child elements (revision, id, contributor, timestamp, text, etc.)
    must use the MediaWiki XML namespace {http://www.mediawiki.org/xml/export-0.11/}
    as a prefix. Without it, importDump.php silently ignores the revisions and
    creates an empty page. The <model>wikitext</model> and <format>text/x-wiki</format>
    elements are also required for MW 1.35's MCR slot storage.
    """
    ns = "{http://www.mediawiki.org/xml/export-0.11/}"
    outtitle = outtitle or title
    # Start by trying to export the given page to get the structure
    xml_params = {
        "action": "query",
        "export": "title",
        "exportnowrap": True,
        "titles": title,
    }
    header = ET.fromstring(
        session.get(url=get_config()["actionapi"], params=xml_params).text
    )
    page = header[1]
    for child in list(page):
        if child.tag not in (f"{ns}title", f"{ns}ns"):
            page.remove(child)
        if child.tag == f"{ns}title":
            child.text = outtitle
        pass
    revid = 1000
    for rev in revs:
        revision = ET.SubElement(page, f"{ns}revision")
        id = ET.SubElement(revision, f"{ns}id")
        id.text = str(revid)
        # Revids are used here only as a reference by parent
        if revid != 1000:
            parentid = ET.SubElement(revision, f"{ns}parentid")
            parentid.text = str(revid - 1)
        revid += 1
        model = ET.SubElement(revision, f"{ns}model")
        model.text = "wikitext"
        format_el = ET.SubElement(revision, f"{ns}format")
        format_el.text = "text/x-wiki"
        author = ET.SubElement(revision, f"{ns}contributor")
        username = ET.SubElement(author, f"{ns}username")
        username.text = rev["author"].get("name", "Unknown user")
        time = ET.SubElement(revision, f"{ns}timestamp")
        time.text = rev["timestamp"]
        if "editsummary" in rev:
            summary = ET.SubElement(revision, f"{ns}comment")
            summary.text = rev["editsummary"]
        if rev.get("minor", False):
            ET.SubElement(revision, f"{ns}minor")
        text = ET.SubElement(revision, f"{ns}text")
        text.text = rev["content"]["content"]
    with open(outfile, "wb") as file:
        file.write(ET.tostring(header, encoding="utf8"))


def getModReason(rev):
    reason = rev["properties"]["moderated-reason"]
    if type(reason) is str:
        reason = json.loads(reason)
    return reason["plaintext"]


def addNullRevisions(
    revs: list,
    namespace: int | None = None,
    title: str | None = None,
    pageid: int | None = None,
    year: int | None = None,
):
    """Add null revisions (i.e protections, page moves, etc.) from the given page to the given set of revisions"""
    # Is this a good idea? It is for the main board, but is it for topics?
    cur = get_connection().cursor()
    if pageid:
        query = f"where rev_page={pageid}"
    else:
        query = f"where page_namespace={namespace} and page_title='{title}'"
    if year:
        query += f" and rev_timestamp like '{year}%'"
    # Include all revisions except Flow talk page manager initialization edits
    # But include Flow talk page manager archival moves
    # and exclude an old 2014-era bug where Flow initializations got attributed to random people. Sorry.
    cur.execute(f"""
        select actor_name,comment_text,rev_timestamp,rev_minor_edit from revision join page on page_id=rev_page
        join comment on comment_id=rev_comment_id
        join actor on actor_id=rev_actor
        {query}
        and (actor_name != "Flow talk page manager" or comment_text like '%moved page%')
        and comment_text != "/* Taken over by Flow */"
        and comment_text not like "%T101583%"
    """)
    toadd = []
    for name, summary, timestamp, minor in cur:
        try:
            name = name.decode("utf8")
        except AttributeError:
            assert type(name) is str
        summary = summary.decode("utf8")
        timestamp = timestamp.decode("ascii")
        # Content is empty since it will get mergeRevisions-ed with real content later
        toadd.append(
            {
                "author": {"name": name},
                "editsummary": summary,
                "timestamp": timestamp,
                "content": {"content": ""},
                "minor": minor,
            }
        )
    return mergeRevisions(revs, toadd)


# Ugly hardcoded whitelist for topics that are corrupt but weren't found Until after read-only ...
corrupt = {}  # {"vevmtczug64s9xcs",}


def convertTopic(root: str, year: int | None = None):
    """Convert a topic from Flow into a set of wikitext revisions"""
    
    if root in corrupt: return ([])
    
    topictitle = "Topic:" + root
    topic_history_params = {
        "action": "flow",
        "submodule": "view-topic-history",
        "page": topictitle,
        "vthformat": "wikitext",
        "format": "json",
        "limit": 5000,  # The API thinks this parameter is ignored, but looking at the code it actually reads
        # an unadorned "limit" parameter (via $wgRequest->getLimitForUser) despite it being completely undocumented.
        # I'll take it ...
    }
    allRevisions = apicall(
        topic_history_params,
        "flow",
        "view-topic-history",
        "result",
        "topic",
        "revisions",
    )
    blocks = {root: {"body": "", "children": [], "signature": ""}}
    resolved = False
    summary = None
    hidden = False
    revisionsWikitext = []
    deleted_posts = set()
    first = True
    # Do some skullduggery to get the initial version of the title
    post_history_params = {
        "action": "flow",
        "submodule": "view-post-history",
        "page": topictitle,
        "vphformat": "wikitext",
        "vphpostId": root,
        "format": "json",
        "limit": 5000,
    }
    titleRevs = apicall(
        post_history_params, "flow", "view-post-history", "result", "topic", "revisions"
    )
    title = titleRevs[-1]["content"]["content"]
    for revision in allRevisions[::-1]:
        match revision["changeType"]:
            case "reply":
                revid = revision["revisionId"]
                assert revid not in blocks
                if first:
                    if year:
                        ryear = int(revision["timestamp"][: len(str(year))])
                        if ryear < year:
                            # Exclude this topic
                            return []
                        elif ryear > year:
                            # Exclude this topic and all ones after it (since we order oldest-first)
                            raise HitThreshold(ryear)
                    editsummary = "New section"
                    first = False
                else:
                    editsummary = "Added reply"
                if revision["content"]["content"]:
                    blocks[revid] = {
                        "body": revision["content"]["content"],
                        "children": [],
                        "signature": getSignature(revision),
                    }
                    try:
                        blocks[revision["replyToId"]]["children"].append(revid)
                    except KeyError:
                        # This happens on some old LQT imports from 2011 for some reason
                        warnings.append(
                            f"Topic:{root}: {revid} is not properly parented!"
                        )
                        blocks[root]["children"].append(revid)
                else:
                    # It isn't possible to add an empty post so if we get a blank here it is a post that in its end state the script can't see
                    # So rewrite the history to pretend it never happened
                    deleted_posts.add(revid)
                    continue
            # edit-post is the standard, flow-edit-post is an old pre-2015 legacy format
            # the number of oddballs there is getting kind of annoying ...
            case "edit-post" | "flow-edit-post":
                postID = revision["postId"]
                if postID in deleted_posts:
                    continue
                assert postID in blocks
                content = revision["content"]["content"]
                if (
                    revision["author"].get("name", "Unknown user")
                    == "Flow talk page manager"
                ):
                    oldContent = blocks[postID]["body"]
                    if content[: len(oldContent)] == oldContent:
                        stray = content[len(oldContent) :]
                        if "LQT post imported with different signature user" in stray:
                            blocks[postID]["ignoreme"] = stray
                            # ... don't even add a null revision
                            continue
                if "ignoreme" in blocks[postID]:
                    content = content.replace(blocks[postID]["ignoreme"], "")
                blocks[postID]["body"] = content
                editsummary = "Edited post"
            case "lock-topic" | "close-topic":
                # lock- is standard, close- is some pre-2014 oddity?
                assert not resolved
                resolved = True
                editsummary = "Marked topic as resolved"
                try:
                    title = revision["content"]["content"]
                except KeyError:
                    pass
            case "restore-topic":
                if resolved and hidden:
                    # Corner case?
                    warnings.append(
                        f"Found resolved-and-hidden topic: {root}. XML for it may be incorrect"
                    )
                    try:
                        editsummary = getModReason(revision)
                    except Exception:
                        warnings.append(traceback.format_exc())
                        editsummary = "Reopened topic"
                    resolved = hidden = False
                elif resolved:
                    resolved = False
                    editsummary = "Reopened topic"
                else:
                    hidden = False
                    # ICK ...
                    editsummary = getModReason(revision)
            case "create-topic-summary":
                if summary:
                    warnings.append(f"create-topic-summary twice for Topic:{root}")
                summary = revision["content"]["content"]
                editsummary = "Created topic summary"
            case "edit-topic-summary":
                summary = revision["content"]["content"]
                editsummary = "Edited topic summary"
            case "hide-topic" | "delete-topic":
                hidden = True
                try:
                    editsummary = revision["moderateReason"]["content"]
                except KeyError:
                    # Another old legacy format. Sigh.
                    editsummary = getModReason(revision)
            case "edit-title":
                title = revision["content"]["content"]
                editsummary = "Edited title"
            case "delete-post":
                if revision["postId"] in deleted_posts:
                    # Hide old transient noise
                    continue
                blocks[revision["postId"]]["hidden"] = True
                try:
                    editsummary = revision["moderateReason"]["content"]
                except KeyError:
                    # Another old legacy format. Sigh.
                    editsummary = getModReason(revision)
            case "hide-post":
                if revision["postId"] in deleted_posts:
                    # Looks like the non-admins were first
                    continue
                blocks[revision["postId"]]["hidden"] = True
                try:
                    editsummary = revision["moderateReason"]["content"]
                except KeyError:
                    # Another old legacy format. Sigh.
                    editsummary = getModReason(revision)
            case "restore-post":
                if revision["postId"] in deleted_posts:
                    # ... I guess people wheel warred?
                    continue
                blocks[revision["postId"]]["hidden"] = False
                editsummary = getModReason(revision)
            case _:
                raise ValueError(revision["changeType"])
        editsummary = f"/* {title} */ {editsummary}"
        rev = {
            "author": {"name": revision["author"].get("name", "Unknown user")},
            "timestamp": revision["timestamp"],
            "content": {
                "content": getText(blocks, root, title, resolved, summary, hidden)
            },
            "editsummary": editsummary,
        }
        revisionsWikitext.append(rev)
    revisionsWikitext = addNullRevisions(
        revisionsWikitext, namespace=2600, title=root.capitalize()
    )
    return revisionsWikitext


@functools.cache
def getUserSignature(username: str, userid: int):
    """Get the signature of a given user."""
    year = str(time.localtime().tm_year)
    nickname = username
    try:
        ipaddress.ip_address(username)
    except ValueError:
        cur = get_connection().cursor()
        cur.execute(
            f"select up_property, up_value from user_properties where up_user={userid}"
        )
        fancysig = False
        for name, value in cur:
            name = name.decode("ascii")
            if name == "fancysig":
                fancysig = int(value)
            elif name == "nickname":
                nickname = value.decode("utf8")
        if fancysig:
            sig = nickname
            hasYear = year in sig
            # In case people use a subst as their signature (which is stupid, but blargh)
            parseAPI = {
                "action": "parse",
                # Ideally we would use the board title here, but the number of people with title-dependent substs in their signature
                # is low enouh that I don't care
                "text": sig,
                "onlypst": 1,
                "format": "json",
                "formatversion": 2,
                "contentmodel": "wikitext",
            }
            sig = apicall(parseAPI, "parse", "text")
            assert type(sig) == str, sig
            if year in sig and not hasYear:
                # Certain people try to manually include the timestamp in their signature field for some reason
                # This won't work here (it will eval to the time the script is run) so just punt
                # and fall back to the default signature
                sig = f"[[User:{username}|{username}]] ([[User talk:{username}|talk]])"
        else:
            nickname = nickname or username
            # Subset of wfEscapeWikitext only including patterns reasonable to expect in signatures
            # (because kghbln's signature is [[kgh]] which needs escaping)
            nickname = nickname.translate(
                {
                    ord("["): "&#91;",
                    ord("]"): "&#93;",
                    ord("<"): "&#60;",
                    ord(">"): "&#62;",
                    ord("{"): "&#123;",
                    ord("|"): "&#124;",
                    ord("}"): "&#125;",
                }
            )
            sig = f"[[User:{username}|{nickname}]] ([[User talk:{username}|talk]])"
    else:
        sig = f"[[Special:Contributions/{username}|{username}]] ([[User talk:{username}|talk]])"
    return sig


def getSignature(revision: dict):
    """Get the signature of a revision, either from the user properties database or from the LQT api"""
    # Read the signature from the LQT database for legacy threads if possible

    cur = get_connection().cursor()
    query = f"""select page_title from page join redirect on page_id=rd_from
                where rd_namespace=2600 and rd_title='{revision["workflowId"].capitalize()}'
                and rd_fragment='flow-post-{revision["revisionId"]}'
                and page_namespace=90
                and exists (select 1 from revision join actor on rev_actor=actor_id 
                    where actor_name='Flow talk page manager' and rev_page=page_id
                )
                """
    cur.execute(query)
    rows = cur.fetchall()
    if len(rows) == 1:
        # Found a legacy LQT post, grab its signature instead
        # For a few corner cases there are two legacy redirects. In that case just punt
        # and fall back to reading the user's current signature
        ((thread,),) = rows
        thread = "Thread:" + thread.decode("utf8")
        lqt_params = {
            "action": "query",
            "list": "threads",
            "throot": thread,
            "thprop": "signature",
            "format": "json",
        }
        threads = apicall(lqt_params, "query", "threads")
        (thread,) = threads.values()
        sig = thread["signature"]
    else:
        sig = getUserSignature(
            revision["author"].get("name", "Unknown user"), revision["author"]["id"]
        )
    date = revision["dateFormats"]["timeAndDate"]
    sig = f"{sig} {date} (UTC)"
    return sig


def indent_carefully(body, indent):
    indentchar = ":" * indent
    in_pre_mode = in_sh_mode = in_nowiki_mode = False
    lines = []
    for line in body.splitlines():
        if not line:
            continue
        # Various stupid hacks ...
        if line == "<pre><nowiki>" or line == "&lt;pre&gt;<nowiki>":
            line = "<pre>"
        if line == "</nowiki></pre>" or line == "</nowiki>&lt;/pre&gt;":
            line = "</pre>"
        if not in_pre_mode and not in_sh_mode and not in_nowiki_mode:
            # Workaround parsoid garbling of pre tags
            line = line.replace("&lt;pre&gt;", "<pre>")
            if line.startswith(" ") and len(line.strip()) > 0:
                # Indent pre doesn't work here (the comment that triggered this would still render wrong)
                # but that's Parsoid's fault.
                line = "<code>" + line + "</code>"
            line = indentchar + line
        if line == "<nowiki><pre></nowiki>" or line == "<nowiki></pre></nowiki>":
            # Is this parsoid's fault? The user entering bad data? Who knows?
            lines.append(line)
            continue
        if in_pre_mode:
            line = line.replace("&lt;/pre&gt;", "</pre>")
        pre_count = line.count("<pre") - line.count("</pre>")
        sh_count = (
            line.count("<syntaxhighlight")
            + line.count("<source")
            - line.count("</syntaxhighlight>")
            - line.count("</source>")
        )
        nowiki_count = line.count("<nowiki>") - line.count("</nowiki>")
        assert not (pre_count and sh_count)
        match pre_count:
            case 1:
                assert not in_pre_mode
                assert (
                    "<syntaxhighlight" not in line and "</syntaxhighlight" not in line
                )
                line = line.replace('<pre style="white-space: pre-wrap;">', "<pre>")
                rindex = line.rindex("<pre>")
                line = (
                    line[:rindex] + "<syntaxhighlight lang='text'>" + line[rindex + 5 :]
                )
                in_pre_mode = True
            case 0:
                if in_pre_mode:
                    if line.startswith("</pre>") and line.endswith("<pre>"):
                        assert "syntaxhighlight" not in line
                        line = (
                            "</syntaxhighlight>"
                            + line[6:-5]
                            + "<syntaxhighlight lang='text'>"
                        )
                    else:
                        for nope in (
                            "<pre>",
                            "</pre>",
                            "<syntaxhighlight",
                            "</syntaxhighlight",
                        ):
                            assert nope not in line
            case -1:
                assert (
                    "<syntaxhighlight" not in line and "</syntaxhighlight" not in line
                )
                assert in_pre_mode
                idx = line.index("</pre>")
                line = line[:idx] + "</syntaxhighlight>" + line[idx + 6 :]
                in_pre_mode = False
            case _:
                assert False, f"Got confused about pre tags"
        match sh_count:
            case 1:
                assert not in_sh_mode
                in_sh_mode = True
            case 0:
                pass
            case -1:
                assert in_sh_mode
                in_sh_mode = False
            case _:
                assert False, "Got confused about sh tags"
        match nowiki_count:
            case 1:
                assert not in_nowiki_mode
                in_nowiki_mode = True
            case 0:
                pass
            case -1:
                if not in_nowiki_mode:
                    warnings.append(f"Unpaired </nowiki> tag in ({line})")
                in_nowiki_mode = False
            case _:
                assert False, "Got confused about nowiki tags"
        assert (in_pre_mode + in_sh_mode + in_nowiki_mode) < 2
        lines.append(line)
    return "\n".join(lines)


def getText(
    blocks: dict,
    root: str,
    title: str,
    resolved: bool,
    summary: str | None,
    hidden: bool,
):
    if hidden:
        return ""
    titleText = f"== {title} =="
    summaryText = trailer = ""
    conf = get_config()
    if summary:
        if resolved:
            summaryText = conf["archivetop_summary_template"].replace(
                "$summary", summary
            )
            trailer = "\n" + conf["archivebottom_template"]
        else:
            summaryText = conf["summary_template"].replace("$summary", summary) + "\n"
    elif resolved:
        summaryText = conf["archivetop_template"]
        trailer = "\n" + conf["archivebottom_template"]

    def getPosts(base, indent):
        if blocks[base].get("hidden", False):
            # If a hidden post has children this will look ugly but there's no good way of representing that
            text = ""
        else:
            signature = blocks[base]["signature"]
            body = blocks[base]["body"]
            # Sometimes people try to add their signature manually to Flow boards even though
            # it isn't needed. Work around that.
            for siglike in [
                "~~~~",
                "<nowiki>~~~~</nowiki>",
                "<nowiki>--~~~~</nowiki>",
                "<nowiki>-- ~~~~</nowiki>",
                "<nowiki>~~~~ </nowiki>",
            ]:
                if body.endswith(siglike):
                    body = body[: -len(siglike)]
                    body = body.strip()
                    break
            for siglike in ["--~~~</nowiki>", "-- ~~~</nowiki>", "~~~</nowiki>"]:
                if body.endswith(siglike):
                    body = body[: -len(siglike)] + "</nowiki>"
                    break
            if "(UTC)" in body[-10:]:
                # If it looks like there's already a signature there then don't add another one
                # Some people use odd signatures that put the timestamp part in italics for example
                # so look near the end too
                signature = ""
            if indent > 0:
                try:
                    body = indent_carefully(body, indent)
                except Exception:
                    line = f"Error indenting post on Topic:{root}"
                    if line not in warnings:
                        warnings.append(line)
                        warnings.append(traceback.format_exc())
                    # Least-bad thing to do is to just post it unindented, so with body unchanged ...
            else:
                body = body.replace("\n&lt;pre&gt;", "\n<pre>")
                body = body.replace("&lt;pre&gt;\n", "<pre>\n")
                body = body.replace("\n&lt;/pre&gt;", "\n</pre>")
            if (
                signature
                and indent == 0
                and body
                and body.splitlines()[-1].startswith("<!-- Message sent by")
            ):
                # Apparently some topics have no content so body is empty. Don't crash then - let the empty post save
                text = (
                    body + "\n" + signature
                )  # Strictly we could omit the sig as redundant here in many cases
                # but MassMessage can post anything so to be safe ...
            elif signature:
                text = body + " " + signature
            else:
                text = body
        first = True
        for child in blocks[base]["children"]:
            # For the very first post, don't overindent it
            # unless it has children, in which case punt
            # Also handle the imported LQT structure where the base has only one child
            # and don't overindent it
            # This can dirty-diff by adding extra indenting in some edge cases (if a hidden post is added
            # in a clashing place, for example), but is better than anything else since the data model
            # gets in the way
            if (
                base == root
                and first
                and (
                    not blocks[child]["children"] or len(blocks[base]["children"]) == 1
                )
            ):
                posts = getPosts(child, indent)
            else:
                posts = getPosts(child, indent + 1)
            first = False
            if posts:
                text = text + "\n" + posts
        return text

    blocksText = getPosts(root, 0)
    return f"{titleText}\n{summaryText}{blocksText}{trailer}"


class PageTooLarge(Exception):
    pass


def mergeRevisions(
    revs1: list, revs2: list, *, revs1default: str = "", maxsize: int | None = None
):
    infinity = "9" * 14
    zero = "0" * 14
    if revs1 == []:
        if revs1default:
            merged = revs2.copy()
            for revision in merged:
                content = revision["content"]["content"]
                revision["content"] = {"content": f"{revs1default}{content}"}
            return merged
        return revs2
    elif revs2 == []:
        return revs1
    revs1 = [
        {"timestamp": zero, "content": {"content": revs1default}},
        *revs1,
        {"timestamp": infinity, "content": revs1[-1]["content"]},
    ]
    revs2 = [
        {"timestamp": zero, "content": {"content": ""}},
        *revs2,
        {"timestamp": infinity, "content": revs2[-1]["content"]},
    ]
    merged = []
    revs1pos = revs2pos = 0
    while True:
        time1 = revs1[revs1pos + 1]["timestamp"]
        time2 = revs2[revs2pos + 1]["timestamp"]
        if time1 == infinity and time2 == infinity:
            return merged
        if time1 < time2:
            revs1pos += 1
            revision = revs1[revs1pos]
        else:
            revs2pos += 1
            revision = revs2[revs2pos]
        mergedrev = revision.copy()
        content1 = revs1[revs1pos]["content"]["content"]
        content2 = revs2[revs2pos]["content"]["content"]
        if content1 and content2:
            content = f"{content1}\n\n{content2}"
        else:
            content = content1 + content2
        if maxsize and len(content) > maxsize:
            raise PageTooLarge
        mergedrev["content"] = {"content": content}
        merged.append(mergedrev)


def mungeLqtArchive(lqt_pages: list[str], lastcontent: str = "") -> tuple[list, str]:
    """Convert the history of a /LQT Archive 1 page at one of these page titles to a Flow page. If none exists, then default on lastcontent"""
    conf = get_config()
    global skip_header
    if skip_header:
        return [], conf["header_lqt_past"] + "\n"
    get_pages_params = {
        "action": "query",
        "titles": "|".join(lqt_pages),
        "prop": "info",
        "format": "json",
    }
    pages = apicall(get_pages_params, "query", "pages")
    pageid = None
    for page in pages.values():
        if "missing" in page or "redirect" in page or "invalidreason" in page:
            # Ignore nonexistent or redirects
            # Also ignore invalid page titles because vandals are endlessly creative
            pass
        elif pageid:
            raise RuntimeError("Found conflicting LQT Archive pages!")
        else:
            pageid = page["pageid"]
    if not pageid:
        return [], lastcontent.replace(conf["header_flow_past"], "").replace(
            "{{#useliquidthreads:1}}", conf["header_lqt_past"]
        ).replace("{{#UseLiquidThreads:1}}", conf["header_lqt_past"])
    get_history_params = {
        "action": "query",
        "pageids": pageid,
        "format": "json",
        "prop": "revisions",
        "rvprop": "flags|timestamp|user|comment|content",
        "rvlimit": "max",
    }
    found_archival = False
    safe_ignore_revs = 2
    default = conf["header_lqt_past"]  # Should never matter, but just in case
    revisionsConverted = []
    printed_warning = get_config()["skip_lqt_early_warning"]
    revdel_check = False
    while True:
        json = apicall(get_history_params)
        revs = json["query"]["pages"][str(pageid)]["revisions"]
        for revision in revs:
            if (
                revision["user"] == "Flow talk page manager"
                and "Conversion of LQT to Flow from" in revision["comment"]
            ):
                found_archival = True
                continue
            if found_archival:
                try:
                    content = revision["*"]
                except KeyError:
                    # It's revdelled.
                    assert "texthidden" in revision
                    revdel_check = True
                    continue

                content = content.replace(
                    "{{#UseLiquidThreads:1}}", "{{#useliquidthreads:1}}"
                )
                # FIXME: These assumptions don't work on ptwikibooks
                if "{{#useliquidthreads:1}}" in content:
                    content = content.replace(
                        "{{#useliquidthreads:1}}", conf["header_lqt_past"]
                    )
                elif len(content) > 50:
                    if not printed_warning:
                        warnings.append(
                            "Found suspicious early history in /LQT Archive 1"
                        )
                        printed_warning = True
                else:
                    safe_ignore_revs -= 1
                    if safe_ignore_revs <= 0 and not printed_warning:
                        warnings.append(
                            "Found suspicious early history in /LQT Archive 1"
                        )
                        printed_warning = True
                    # For the one or two pre-LQT revisions I don't need a header of any kind I guess
                    # And they should start, so set default = ""
                    default = ""
                if revdel_check:
                    revdel_check = False
                    if content == revisionsConverted[-1]["content"]["content"]:
                        # Ignore the revdelled revision and the one that reverts it
                        # (as spam/vandalism/copyvio/etc) entirely
                        del revisionsConverted[-1]
                    else:
                        # This will be awkward ...
                        warnings.append("Could not see through revision deletion.")
                        revdel_check = False
                rev = {
                    "author": {"name": revision["user"]},
                    "timestamp": revision["timestamp"],
                    "content": {"content": content},
                    "editsummary": revision["comment"],
                }
                if "minor" in revision:
                    rev["minor"] = revision["minor"]
                # Munge the API's nicely-formatted timestamp to get it in the same place as the others which use bare 14-char format
                # (or else mergeRevisions will barf later)
                ts = rev["timestamp"]
                ts = (
                    ts.replace(":", "")
                    .replace("Z", "")
                    .replace("-", "")
                    .replace("T", "")
                )
                rev["timestamp"] = ts
                revisionsConverted.append(rev)
        if "continue" in json:
            warnings.append(
                "Continuing history enumeration of /LQT Archive 1 page. This should not normally happen"
            )
            get_history_params.update(json["continue"])
        else:
            break
    assert found_archival
    return revisionsConverted, default


class HitThreshold(Exception):
    pass


@functools.cache
def get_topiclist_blocks(page, yearlen):
    get_topiclist_params = {
        "action": "flow",
        "submodule": "view-topiclist",
        "page": page,
        "format": "json",
        "vtllimit": "max",
        "vtlsortby": "newest",
    }
    roots = []
    while True:
        topiclist = apicall(
            get_topiclist_params, "flow", "view-topiclist", "result", "topiclist"
        )
        for root in topiclist["roots"]:
            rev = topiclist["revisions"][topiclist["posts"][root][0]]
            if rev["changeType"] == "new-post" and not rev["previousRevisionId"]:
                topicyear = int(rev["timestamp"][:yearlen])
                roots.append((root, topicyear))
            else:
                roots.append([root, None])
        # This is awful, but it matches what convertToText does, and there doesn't seem to be a better way
        try:
            pagination = topiclist["links"]["pagination"]
            if not pagination:
                break
            url = pagination["fwd"]["url"]
            index = url.find("topiclist_offset-id")
            get_topiclist_params["vtloffset-id"] = url[index + 20 : index + 36]
        except KeyError:
            break
    return roots


def convert_from_topiclist(page, year):
    revisions, default = convertHeader(page, year)
    yearlen = len(str(year))
    topiclist = get_topiclist_blocks(page, yearlen)
    pages = apicall(
        {"action": "query", "titles": page, "format": "json"}, "query", "pages"
    )
    (v,) = pages.values()
    interesting = []
    for blob in topiclist:
        root, when = blob
        if root in corrupt:
            continue
        if when is None:
            try:
                convertTopic(root, int("1" * yearlen))
            except HitThreshold as e:
                when = e.args[0]
                blob[:] = [root, when]
            else:
                import pdb

                pdb.set_trace()
                raise RuntimeError
        if when > year:
            # Keep looking ...
            pass
        elif when == year:
            # Aha!
            interesting.append(root)
        else:
            # We've overshot!
            break
    for root in interesting[::-1]:
        revisions = mergeRevisions(
            revisions, convertTopic(root, year), revs1default=default
        )
    pages = apicall(
        {"action": "query", "titles": page, "format": "json"}, "query", "pages"
    )
    (v,) = pages.values()
    corePageId = v["pageid"]
    revisions = addNullRevisions(revisions, pageid=corePageId, year=year)
    return revisions


def convertBoard(page: str, year: int | None = None, maxsize: int | None = None):
    """Convert an entire Flow board to wikitext with history"""
    get_topiclist_params = {
        "action": "flow",
        "submodule": "view-topiclist",
        "page": page,
        "format": "json",
        "vtllimit": "max",
        "vtlsortby": "newest",
    }
    revisions, default = convertHeader(page, year)
    roots = []
    hit_end = False
    while True:
        topiclist = apicall(
            get_topiclist_params, "flow", "view-topiclist", "result", "topiclist"
        )
        if year:
            # Quick check for topics that can be easily excluded without another API call
            topicyear = 9999999
            for root in topiclist["roots"]:
                rev = topiclist["revisions"][topiclist["posts"][root][0]]
                if rev["changeType"] == "new-post" and not rev["previousRevisionId"]:
                    topicyear = int(rev["timestamp"][: len(str(year))])
                    if topicyear == year:
                        roots.append(root)
                else:
                    roots.append(root)
            if topicyear < year:
                # Since we order topics newest-first if we're too far in the base we're done here
                break
        else:
            roots.extend(topiclist["roots"])
        # This is awful, but it matches what convertToText does, and there doesn't seem to be a better way
        try:
            pagination = topiclist["links"]["pagination"]
            if not pagination:
                break
            url = pagination["fwd"]["url"]
            index = url.find("topiclist_offset-id")
            get_topiclist_params["vtloffset-id"] = url[index + 20 : index + 36]
        except KeyError:
            break
    for root in roots[::-1]:
        try:
            revisions = mergeRevisions(
                revisions,
                convertTopic(root, year),
                revs1default=default,
                maxsize=maxsize,
            )
        except HitThreshold:
            break
    pages = apicall(
        {"action": "query", "titles": page, "format": "json"}, "query", "pages"
    )
    (v,) = pages.values()
    corePageId = v["pageid"]
    revisions = addNullRevisions(revisions, pageid=corePageId, year=year)
    return revisions


def finalize(revs):
    # Finalize is inserting a new line randomly. Disable it.
    # return
    flow = 0
    lqt = 0
    conf = get_config()
    for revision in revs:
        content = revision["content"]["content"]
        if len(content) == 0 and not conf["straight_from_lqt"]:
            # This case is logically impossible in straight_from_lqt mode
            warning = "Found empty revision, probably needs rescuing from old DB dump"
            if warning not in warnings:
                warnings.append(warning)
        if conf["header_flow_past"] in content:
            flow += 1
        elif conf["header_lqt_past"] in content:
            lqt += 1
    if flow > 0 and conf["straight_from_lqt"]:
        raise RuntimeError(
            "Flow revisions should not be present in straight_from_lqt mode"
        )
    final = conf["header_flow_present"] if flow >= lqt else conf["header_lqt_present"]
    lastcontent = revs[-1]["content"]["content"]
    if "{{Flow-enabled}}" in content or "{{flow-enabled}}" in content:
        # Some pages already had {{flow-enabled}} ...
        # This is a hack for a specific wiki where the header template name was reused
        # which is why it doesn't use conf.
        final = ""
    content = lastcontent
    if conf["header_flow_past"]:
        content = content.replace(conf["header_flow_past"], final)
    if conf["header_lqt_past"]:
        content = content.replace(conf["header_lqt_past"], final)
    if content != lastcontent:
        revs.append(
            {
                "content": {"content": content},
                "timestamp": time.ctime(time.time() - 1),
                "author": {"name": "Genderiyya maintenance script"},
                "editsummary": "Finalize header after export",
            }
        )


skip_header = False


def main(args: list[str]):
    _init_session()
    page = args[1]
    outfile = args[2]
    if len(args) > 3 and args[3] == "--skiplqta":
        global skip_header
        skip_header = True
        del args[3]
    try:
        year = int(args[3]) if len(args) > 3 else None
        if year:
            if len(args) > 4:
                outtitle = args[4]
            else:
                outtitle = page + "/" + str(year)
        else:
            outtitle = page
    except ValueError:
        outtitle = args[3]
        year = None
    revs = convertBoard(page, year)
    print(revs)
    finalize(revs)
    for warning in warnings:
        print(warning)
    exportToXML(page, revs, outfile, outtitle)


if __name__ == "__main__":
    main(sys.argv)
