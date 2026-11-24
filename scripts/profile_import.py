"""Read active ROS record logs without opening or modifying their cached databases."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def lines(path):
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig") as file:
        for index, line in enumerate(file, 1):
            try:
                yield json.loads(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{index}: invalid JSON") from exc


def import_records(db, projects, capability, ask, assess, mappings=None):
    files = sorted(projects.glob("*/events.jsonl"))
    if (projects/"events.jsonl").is_file():
        files = [projects/"events.jsonl"]
    if not files:
        raise ValueError("no ROS record event logs found")
    counts = Counter(records=len(files))
    withheld = []
    normalized = set()
    for path in files:
        graph = {row["id"]:row for row in lines(path.parent/"graph"/"nodes.jsonl")}
        attempts, grades, helped = {}, {}, set()
        for event in lines(path):
            data, typ = event["data"], event["type"]
            pair = (data.get("lesson"),event["subject"])
            if typ in ("hint","reveal"):
                helped.add(pair)
            elif typ == "retrieval":
                counts["summary_only"] += 1
            elif typ == "attempt":
                attempts[event["id"]] = (event,pair in helped)
            elif typ == "grade":
                grades[data.get("attempt")] = event
                counts["grades"] += 1
        counts["ungraded_attempts"] += len(attempts.keys() - grades.keys())
        for key, grade in grades.items():
            verdict = {"correct":"correct","partially-correct":"partial","incorrect":"incorrect"}.get(grade["data"].get("verdict"))
            original, hinted = attempts.get(key, ({}, False))
            data = original.get("data", {})
            item_id = grade["subject"]
            response = data.get("response")
            reason = None
            if not verdict or original.get("actor") != "learner" or not grade.get("actor") or grade.get("actor") == "learner":
                reason = "missing learner/grade provenance"
            elif original.get("subject") != item_id or grade["data"].get("lesson") != data.get("lesson"):
                reason = "different lesson or item"
            elif response is None and not data.get("dont_know"):
                reason = "missing learner answer"
            elif not re.fullmatch(r"[0-9a-f]{64}", item_id):
                reason = "invalid item ID"
            else:
                item_file = path.parent/"items"/(item_id+".json")
                if not item_file.is_file():
                    reason = "missing question"
                else:
                    item = json.loads(item_file.read_text(encoding="utf-8"))
                    hashed = {k:v for k,v in item.items() if k not in ("id","meta")}
                    digest = hashlib.sha256(json.dumps(hashed,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
                    if digest != item_id:
                        reason = "item hash mismatch"
            if reason:
                withheld.append({"record":path.parent.name,"attempt":key,"reason":reason})
                continue
            legacy_id = data.get("legacy_event","").removeprefix("import-")
            normalized_id = legacy_id or key
            if normalized_id in normalized:
                counts["duplicate_originals"] += 1
                continue
            caps = [cap for cap in item.get("concepts",[]) if graph.get(cap,{}).get("type") == "capability" and not graph[cap].get("deleted")]
            titles = {cap:graph[cap].get("title") or cap for cap in caps}
            if not caps and item_id in (mappings or {}):
                cap,title = mappings[item_id]
                caps,titles = [cap],{cap:title}
            if len(caps) != 1:
                withheld.append({"record":path.parent.name,"attempt":key,"item":item_id,"reason":"needs a verified single-capability mapping"})
                continue
            cap = capability(db,caps[0],titles[caps[0]])
            # Imported sidecar histories can omit hints; unknown cannot demonstrate independence.
            assistance = "hinted" if hinted else "unknown" if legacy_id else "none"
            mode = "recognition" if item["kind"] == "choice" else "routine"
            response_text = ("I don't know" if response is None else response if isinstance(response,str) else json.dumps(response))
            if not response_text.strip():
                withheld.append({"record":path.parent.name,"attempt":key,"reason":"empty learner answer"})
                continue
            new_key = "ros:"+normalized_id
            source = json.dumps({"record":str(path.parent.resolve()),"attempt":key,"grade":grade["id"],
                                 "item":item_id,"original":original.get("source"),"graded_by":grade["actor"]})
            existing = db.execute("SELECT 1 FROM prompt WHERE id=?", (new_key,)).fetchone()
            ask(db,"ros:"+str(data.get("lesson") or key),new_key,cap,item["prompt"],original["ts"],source)
            assess(db,new_key,response_text,verdict,assistance,mode,
                   grade["data"].get("feedback") or grade["data"].get("rationale") or "Recorded verdict: "+grade["data"]["verdict"],
                   when=original["ts"])
            normalized.add(normalized_id)
            counts["already_present" if existing else "added"] += 1
    return {"counts":dict(counts), "withheld":withheld}
