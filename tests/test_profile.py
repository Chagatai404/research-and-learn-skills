"""Exercise the profile through the same CLI used by agents."""
import concurrent.futures
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/"scripts"/"profile.py"


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name)/"profile.sqlite3"

    def call(self,*args,fail=False,db=None):
        proc = subprocess.run([sys.executable,str(SCRIPT),"--db",str(db or self.db),*args],capture_output=True,text=True)
        if fail:
            self.assertNotEqual(proc.returncode,0)
            return proc.stderr
        self.assertEqual(proc.returncode,0,proc.stderr)
        return json.loads(proc.stdout)

    def test_prerequisite_frontier_and_aliases(self):
        self.call("capability","end","Target")
        self.call("capability","first","First")
        self.call("alias","first","Foundation")
        self.call("require","end","Foundation","needed for proof")
        self.call("require","first","end","cycle",fail=True)
        self.call("goal","term","end")
        self.assertEqual(self.call("find","found")["capabilities"],[{"id":"first","title":"First"}])
        self.assertEqual(self.call("find")["goals"],[{"name":"term"}])
        self.assertEqual(self.call("route","term")["frontier"],["first"])
        self.call("ask","topic","x","Foundation","Question")
        self.assertEqual(self.call("find","top")["pending"][0]["id"],"x")
        self.call("grade","x","Answer","correct","none","routine","reason")
        self.assertEqual(self.call("route","term")["frontier"],["end"])
        self.call("merge","first","end",fail=True)
        self.call("capability","copy","Alternate title")
        self.call("merge","first","copy")
        self.assertEqual(self.call("status","Foundation")["evidence_count"],1)
        self.assertEqual(self.call("route","term")["frontier"],["end"])

    def test_concurrent_resume_grade_and_correction(self):
        self.call("capability","x","Title")
        args=("ask","week","a","x","question","--rubric","criteria")
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=[pool.submit(self.call,*args) for _ in range(2)]
            for f in results:
                f.result()
        self.call("ask","week","b","x","other",fail=True)
        self.call("hint","a","revealed")
        self.call("hint","a","hinted")
        pending=self.call("resume","week")["pending"]
        self.assertEqual((pending["rubric"],pending["help"]),("criteria","revealed"))
        self.call("grade","a","work","correct","none","routine","r",fail=True)
        args=("grade","a","work","correct","revealed","routine","r")
        self.call(*args)
        self.call(*args)
        self.assertIsNone(self.call("resume","week")["pending"])
        self.assertEqual(self.call("status","x")["score"],1)
        self.call("correct","a","1","incorrect","revealed","routine","rechecked")
        self.call("correct","a","1","partial","revealed","routine","bad revision",fail=True)
        h=self.call("history","x")
        self.assertEqual((len(h),h[0]["revision"],h[0]["response"]),(1,2,"work"))
        self.assertEqual(self.call("status","x")["score"],0)

    def test_backup_restore_and_review(self):
        self.call("capability","x","Title")
        self.assertIsNone(self.call("status","x")["score"])
        self.call("ask","s","a","x","q")
        self.call("grade","a","ans","correct","none","delayed","r")
        self.assertEqual(self.call("status","x")["score"],2)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE prompt SET answered='2000-01-01T12:00:00Z'")
        self.assertTrue(self.call("status","x")["due"])
        self.call("ask","s","b","x","different")
        self.call("grade","b","ans","correct","none","delayed","r")
        self.assertEqual(self.call("status","x")["score"],4)
        backup=Path(self.tmp.name)/"backup.db"
        restored=Path(self.tmp.name)/"restored.db"
        self.call("backup",str(backup))
        self.call("restore",str(backup),db=restored)
        self.call("restore",str(backup),db=restored,fail=True)
        self.assertEqual(self.call("history","x"),self.call("history","x",db=restored))


    def test_import_provenance_and_idempotence(self):
        import hashlib
        root = Path(self.tmp.name)/"projects"/"course"
        (root/"items").mkdir(parents=True)
        (root/"graph").mkdir()
        (root/"graph"/"nodes.jsonl").write_text(json.dumps({"id":"cap","type":"capability","title":"Ratio"})+"\n")
        item={"prompt":"Double one half","kind":"numeric","concepts":["cap"]}
        token=hashlib.sha256(json.dumps(item,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        (root/"items"/(token+".json")).write_text(json.dumps(item))
        def event(id,typ,actor,data):
            return dict(id=id,type=typ,ts="2025-01-01T09:00:00Z",actor=actor,subject=token,data=dict(lesson="s",**data))
        events=[
            event("summary","retrieval","learner",{"outcome":"pass"}),
            event("hint","hint","learner",{}),
            event("work","attempt","learner",{"response":1}),
            event("mark","grade","checker",{"attempt":"work","verdict":"correct"}),
            event("fake","attempt","assistant",{"response":1}),
            event("wrong","grade","checker",{"attempt":"fake","verdict":"correct"}),
        ]
        (root/"events.jsonl").write_text("\n".join(map(json.dumps,events))+"\n")
        args=("import-ros",str(root.parent))
        result=self.call(*args)
        self.assertEqual(result["counts"]["added"],1)
        self.assertEqual(result["counts"]["summary_only"],1)
        self.assertEqual(result["withheld"][0]["attempt"],"fake")
        self.call("capability","canonical","Calculate a ratio")
        self.call("merge","cap","canonical")
        self.assertEqual(self.call(*args)["counts"]["already_present"],1)
        evidence,=self.call("history","canonical")
        self.assertEqual(evidence["assistance"],"hinted")
        self.assertEqual((evidence["response"],json.loads(evidence["source"])["grade"]),("1","mark"))
        self.assertEqual(self.call("status","canonical")["score"],1)
