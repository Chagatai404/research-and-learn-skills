"""Switch the former tutor's generated guidance after both native installs."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from note_edit import apply, digest

GUIDANCE = """## Research and learning

Use the installed research-and-learn plugin for course study, independent learning,
research, audit and teach-back. Read the relevant plugin skill before starting.
Use the shared local learner profile for graded evidence and pending prompts.
Use the selected vault's Study and Research index to locate the current week,
topic or investigation. Resume practice in its note. The researcher approves
plans, decides on claims, and chooses whether to waive ownership.
"""

NOTES = """## Course, topic and research practice

Use the research-and-learn plugin's study-note guidance. Resume a course in the
documented syllabus week, independent study in the topic note, and research in
the investigation note. Keep the current prompt, useful original reasoning and
feedback together. The local learner profile holds repetitive graded attempts.
"""


def replacement(content, start, end, section, retain_end=False):
    if content.count(start) != 1 or content.count(end) != 1:
        raise ValueError("Unexpected legacy section boundaries")
    first = content.index(start)
    last = content.index(end, first) + (0 if retain_end else len(end))
    return content[:first] + section.rstrip() + "\n\n" + content[last:].lstrip("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    root = args.home
    backups = Path(__file__).resolve().parents[1] / ".migration" / "host-guidance"
    candidates = [
        (root / ".codex/AGENTS.md", "codex"), (root / ".claude/CLAUDE.md", "claude"),
        (root / ".agents/skills/obsidian/SKILL.md", "notes"),
        (root / ".claude/skills/obsidian/SKILL.md", "notes")]
    edits = []
    seen = set()
    for path, kind in candidates:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        if not path.exists():
            continue
        raw = path.read_bytes()
        body = raw.decode("utf-8").replace("\r\n", "\n")
        if kind == "notes" and NOTES not in body:
            body = replacement(body, "## Tutor / research session notes", "## Decision notes", NOTES, True)
        elif kind == "codex" and GUIDANCE not in body:
            body = replacement(body, "<!-- research-os:begin", "<!-- research-os:end -->", GUIDANCE)
        elif kind == "claude" and GUIDANCE not in body:
            body = body.rstrip() + "\n\n" + GUIDANCE
        else:
            continue
        proposed = body.replace("\n", "\r\n" if b"\r\n" in raw else "\n").encode("utf-8")
        edits.append((path, proposed, digest(raw)))
    for path, data, expected in edits:
        print(path, "backup", expected)
        if args.apply:
            apply(path, data, expected, backups)


if __name__ == "__main__":
    main()
