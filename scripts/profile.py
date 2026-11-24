"""Portable learner evidence and prerequisite routing. Run with --help."""
import argparse

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

DEFAULT = Path.home() / ".research-and-learn" / "profile.sqlite3"
VERDICTS = ("correct", "partial", "incorrect")
ASSISTANCE = ("none", "hinted", "revealed", "unknown")
MODES = ("recognition", "routine", "transfer", "delayed")
SCHEMA = """
CREATE TABLE capability(id TEXT PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE alias(name TEXT PRIMARY KEY COLLATE NOCASE, cap TEXT REFERENCES capability);
CREATE TABLE prerequisite(target TEXT REFERENCES capability, prereq TEXT REFERENCES capability,
 reason TEXT NOT NULL, PRIMARY KEY(target,prereq));
CREATE TABLE goal(name TEXT, cap TEXT REFERENCES capability, PRIMARY KEY(name,cap));
CREATE TABLE prompt(id TEXT PRIMARY KEY, scope TEXT NOT NULL, cap TEXT REFERENCES capability,
 question TEXT NOT NULL, response TEXT, opened TEXT NOT NULL, answered TEXT, source TEXT);
CREATE UNIQUE INDEX one_pending ON prompt(scope) WHERE answered IS NULL;
CREATE TABLE grade(id TEXT REFERENCES prompt, revision INTEGER, verdict TEXT NOT NULL,
 assistance TEXT NOT NULL, mode TEXT NOT NULL, rationale TEXT NOT NULL, entered TEXT NOT NULL,
 PRIMARY KEY(id,revision));
PRAGMA user_version=1;
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path, read_only=False):
    if read_only and path.is_file():
        reader = sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True,timeout=12)
        reader.row_factory = sqlite3.Row
        reader.execute("BEGIN")
        if reader.execute("PRAGMA user_version").fetchone()[0] == 2:
            return reader
        reader.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=12)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("BEGIN IMMEDIATE")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        if db.execute("SELECT name FROM sqlite_master").fetchone():
            raise ValueError("unrecognized database")
        for statement in SCHEMA.split(";"):
            if statement.strip():
                db.execute(statement)
    if version in (0,1):
        db.execute("ALTER TABLE prompt ADD COLUMN rubric TEXT NOT NULL DEFAULT ''")
        db.execute("ALTER TABLE prompt ADD COLUMN help TEXT NOT NULL DEFAULT 'none'")
        db.execute("PRAGMA user_version=2")
    elif version != 2:
        raise ValueError(f"unsupported profile version {version}")
    return db


def resolve(db, name):
    row = db.execute("SELECT cap FROM alias WHERE name=?", (name,)).fetchone()
    if not row:
        raise ValueError(f"unknown capability: {name}")
    return row[0]


def alias(db, cap, name):
    linked = db.execute("SELECT cap FROM alias WHERE name=?", (name,)).fetchone()
    if linked and linked[0] != cap:
        raise ValueError(f"name already belongs to {linked[0]}")
    db.execute("INSERT OR IGNORE INTO alias VALUES (?,?)", (name, cap))


def capability(db, key, title):
    existing = db.execute("SELECT cap FROM alias WHERE name=?", (key,)).fetchone()
    if existing and existing[0] != key:
        # A previous merge keeps the old ID as an alias. Replay uses the merged ID.
        alias(db, existing[0], title)
        return existing[0]
    row = db.execute("SELECT title FROM capability WHERE id=?", (key,)).fetchone()
    if row and row[0] != title:
        raise ValueError(f"{key} already exists under {row[0]}")
    db.execute("INSERT OR IGNORE INTO capability VALUES (?,?)", (key, title))
    for name in (key, title):
        alias(db, key, name)
    return key


def history(db, cap):
    return [dict(row) for row in db.execute("""
      SELECT p.*, g.revision,g.verdict,g.assistance,g.mode,g.rationale FROM prompt p
      JOIN grade g ON p.id=g.id
      WHERE cap=? AND revision=(SELECT MAX(revision) FROM grade WHERE id=p.id)
      ORDER BY answered, opened, p.rowid""", (cap,))]


def status(db, cap):
    rows = history(db, cap)
    score = None
    last_independent = None
    due = None
    for row in rows:
        day = date.fromisoformat(row["answered"][:10])
        if row["verdict"] == "incorrect":
            score = 0
        elif row["verdict"] == "partial" or row["assistance"] != "none" or row["mode"] == "recognition":
            score = 1
        else:
            score = 2
            if row["mode"] == "transfer":
                score = 3
            if row["mode"] == "delayed" and last_independent and day > last_independent:
                score = 4
            last_independent = day
        due = day + timedelta(days=(1, 1, 3, 7, 21)[score])
    return {"capability": cap, "score": score, "evidence_count": len(rows),
            "band": "unknown" if score is None else ("miss", "developing", "demonstrated", "transfer", "retained")[score],
            "last_attempt": rows[-1]["id"] if rows else None, "review_due": str(due) if due else None,
            "due": due is not None and due <= datetime.now(timezone.utc).date(),
            "last_independent": str(last_independent) if last_independent else None}


def ask(db, scope, key, cap, question, opened=None, source=None, rubric=""):
    old = db.execute("SELECT scope,cap,question,rubric FROM prompt WHERE id=?", (key,)).fetchone()
    if old:
        if tuple(old) != (scope, cap, question,rubric):
            raise ValueError("attempt ID already used for another question")
        return
    if db.execute("SELECT 1 FROM prompt WHERE scope=? AND answered IS NULL", (scope,)).fetchone():
        raise ValueError("scope already has an outstanding prompt; resume it first")
    db.execute("INSERT INTO prompt(id,scope,cap,question,opened,source,rubric) VALUES (?,?,?,?,?,?,?)",
               (key, scope, cap, question, opened or now(), source,rubric))


def mark_help(db,key,help_level):
    row = db.execute("SELECT help,answered FROM prompt WHERE id=?", (key,)).fetchone()
    if not row or row["answered"]:
        raise ValueError("help must be recorded on a pending question")
    if row["help"] != "revealed":
        db.execute("UPDATE prompt SET help=? WHERE id=?", (help_level,key))


def assess(db, key, response, verdict, assistance, mode, rationale, revision=0, when=None):
    prompt = db.execute("SELECT response,help FROM prompt WHERE id=?", (key,)).fetchone()
    if not prompt:
        raise ValueError("unknown attempt")
    if prompt["help"] == "revealed" and assistance != "revealed" or prompt["help"] == "hinted" and assistance not in ("hinted","revealed"):
        raise ValueError(f"recorded assistance was {prompt['help']}; include it in the grade")
    old = db.execute("SELECT revision,verdict,assistance,mode,rationale FROM grade WHERE id=? ORDER BY revision DESC LIMIT 1", (key,)).fetchone()
    values = (verdict, assistance, mode, rationale)
    if old and old[0] == revision+1 and tuple(old)[1:] == values and response == prompt[0]:
        return
    if (old[0] if old else 0) != revision:
        raise ValueError("revision conflict; inspect history before grading")
    if revision and prompt[0] != response:
        raise ValueError("learner response is immutable")
    db.execute("UPDATE prompt SET response=?, answered=COALESCE(answered,?) WHERE id=?", (response, when or now(), key))
    db.execute("INSERT INTO grade VALUES (?,?,?,?,?,?,?)", (key, revision+1, *values, when or now()))


def ancestors(db, key):
    return {r[0] for r in db.execute("""WITH RECURSIVE deps(id) AS (
        SELECT prereq FROM prerequisite WHERE target=? UNION
        SELECT p.prereq FROM prerequisite p JOIN deps d ON p.target=d.id)
        SELECT id FROM deps""", (key,))}


def merge(db, source, target):
    """Coalesce synonymous capabilities in one transaction, keeping their evidence."""
    if source == target:
        return
    if source in ancestors(db, target) or target in ancestors(db, source):
        raise ValueError("cannot merge capabilities on the same prerequisite chain")
    edges = db.execute("SELECT * FROM prerequisite WHERE target=? OR prereq=?", (source, source)).fetchall()
    for edge in edges:
        old_target, old_prereq, reason = edge
        pair = (target if old_target == source else old_target, target if old_prereq == source else old_prereq)
        old = db.execute("SELECT reason FROM prerequisite WHERE target=? AND prereq=?", pair).fetchone()
        if old and reason != old[0]:
            reason = old[0] + "\n" + reason
        db.execute("INSERT OR REPLACE INTO prerequisite VALUES (?,?,?)", (*pair,reason))
    db.execute("DELETE FROM prerequisite WHERE target=? OR prereq=?", (source, source))
    db.execute("INSERT OR IGNORE INTO goal SELECT name,? FROM goal WHERE cap=?", (target, source))
    db.execute("DELETE FROM goal WHERE cap=?", (source,))
    db.execute("UPDATE alias SET cap=? WHERE cap=?", (target,source))
    db.execute("UPDATE prompt SET cap=? WHERE cap=?", (target,source))
    db.execute("DELETE FROM capability WHERE id=?", (source,))


def route(db, name):
    roots = [r[0] for r in db.execute("SELECT cap FROM goal WHERE name=?", (name,))]
    if not roots:
        roots = [resolve(db, name)]
    reachable = set(roots)
    for root in roots:
        reachable.update(ancestors(db, root))
    states = {key: status(db, key) for key in sorted(reachable)}
    def ready(key):
        state = states[key]
        return (state["score"] or 0) >= 2 and not state["due"]
    return {"goal": name, "frontier": [key for key in states if not ready(key) and all(ready(a) for a in ancestors(db,key))],
            "capabilities": list(states.values()), "requires": [dict(row) for row in db.execute(
                "SELECT * FROM prerequisite ORDER BY target,prereq") if row["target"] in reachable]}


def copy_profile(source, target):
    if not source.is_file():
        raise ValueError("source profile is missing")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source.resolve().as_uri()+"?mode=ro", uri=True) as original:
        if original.execute("PRAGMA user_version").fetchone()[0] not in (1,2):
            raise ValueError("unsupported source")
        if original.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("source is damaged")
        if target.exists():
            raise ValueError("destination already exists; restore or back up to a fresh path")
        descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".profile-",suffix=".sqlite3")
        os.close(descriptor)
        try:
            duplicate = sqlite3.connect(temporary)
            try:
                original.backup(duplicate)
                if duplicate.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("backup verification failed")
            finally:
                duplicate.close()
            # Publish the completed snapshot atomically. Never replace another host's profile.
            if os.name == "nt":
                # Windows rename fails when the destination exists.
                os.rename(temporary,target)
            else:
                os.link(temporary,target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return {"copied_to": str(target)}


def run(db, cmd, args):
    if cmd == "find":
        term = args.term or ""
        def matches(sql):
            return [dict(row) for row in db.execute(sql, (term,))]
        return {
            "capabilities": matches("""
                SELECT DISTINCT c.id, c.title FROM capability c JOIN alias a ON a.cap=c.id
                WHERE instr(lower(a.name),lower(?)) > 0 ORDER BY c.title"""),
            "goals": matches("SELECT DISTINCT name FROM goal WHERE instr(lower(name),lower(?)) > 0 ORDER BY name"),
            "pending": matches("""
                SELECT scope, id, cap FROM prompt WHERE answered IS NULL AND
                instr(lower(scope || ' ' || cap),lower(?)) > 0 ORDER BY scope"""),
        }
    if cmd == "capability":
        capability(db, args.id, args.title)
    elif cmd == "alias":
        alias(db, resolve(db,args.id), args.name)
    elif cmd == "merge":
        merge(db,resolve(db,args.source),resolve(db,args.target))
    elif cmd == "require":
        target, prereq = resolve(db,args.target), resolve(db,args.prereq)
        if target == prereq or target in ancestors(db, prereq):
            raise ValueError("prerequisite would create a cycle")
        db.execute("INSERT INTO prerequisite VALUES (?,?,?) ON CONFLICT(target,prereq) DO UPDATE SET reason=excluded.reason",
                   (target,prereq,args.reason))
    elif cmd == "goal":
        db.execute("INSERT OR IGNORE INTO goal VALUES (?,?)", (args.name,resolve(db,args.cap)))
    elif cmd == "ask":
        ask(db,args.scope,args.id,resolve(db,args.cap),args.question,rubric=args.rubric)
    elif cmd == "hint":
        mark_help(db,args.id,args.help_level)
    elif cmd == "resume":
        row = db.execute("SELECT id,scope,cap,question,opened,rubric,help FROM prompt WHERE scope=? AND answered IS NULL", (args.scope,)).fetchone()
        return {"pending": dict(row) if row else None}
    elif cmd == "grade":
        assess(db,args.id,args.response,args.verdict,args.assistance,args.mode,args.rationale)
    elif cmd == "correct":
        response = db.execute("SELECT response FROM prompt WHERE id=?", (args.id,)).fetchone()
        if not response or response[0] is None or args.revision < 1:
            raise ValueError("provide the current grade revision")
        assess(db,args.id,response[0],args.verdict,args.assistance,args.mode,args.rationale,args.revision)
    elif cmd == "history":
        return history(db,resolve(db,args.cap))
    elif cmd == "status":
        return status(db,resolve(db,args.cap))
    elif cmd == "route":
        return route(db,args.name)
    elif cmd == "import-ros":
        from profile_import import import_records
        mappings = json.loads(args.mappings.read_text(encoding="utf-8-sig")) if args.mappings else None
        return import_records(db,Path(args.projects),capability,ask,assess,mappings)
    return {"ok": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.getenv("RESEARCH_LEARN_PROFILE",DEFAULT)))
    sub = parser.add_subparsers(dest="cmd",required=True)
    commands = {"capability":"id title","alias":"id name","merge":"source target","require":"target prereq reason","goal":"name cap",
                "route":"name","status":"cap","ask":"scope id cap question","hint":"id help_level","resume":"scope",
                "grade":"id response verdict assistance mode rationale",
                "correct":"id revision verdict assistance mode rationale","history":"cap","backup":"destination",
                "restore":"source","import-ros":"projects","find":""}
    for command, fields in commands.items():
        p = sub.add_parser(command)
        if command == "find":
            p.add_argument("term", nargs="?", help="Search titles, aliases, goals and open scopes by substring")
        if command == "import-ros":
            p.add_argument("--mappings", type=Path, help="JSON object mapping reviewed full item hashes to [capability ID, title]")
        if command == "ask":
            p.add_argument("--rubric",help="Private grading criteria stored for resumption")
        for field in fields.split():
            p.add_argument(field, type=int if field=="revision" else str,
                           choices={"verdict":VERDICTS,"assistance":ASSISTANCE,"mode":MODES,"help_level":("hinted","revealed")}.get(field))
    args = parser.parse_args()
    try:
        if any(isinstance(v,str) and not v.strip() for v in vars(args).values()):
            raise ValueError("supply nonempty text for every field")
        if args.cmd == "ask":
            args.rubric = args.rubric or ""
        if args.cmd == "backup":
            result = copy_profile(args.db,Path(args.destination))
        elif args.cmd == "restore":
            result = copy_profile(Path(args.source),args.db)
        else:
            db = connect(args.db,read_only=args.cmd in {"find","resume","route","history","status"})
            try:
                with db:
                    result = run(db,args.cmd,args)
            finally:
                db.close()
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,sqlite3.Error) as exc:
        parser.exit(1,f"{exc}\n")


if __name__ == "__main__":
    main()

