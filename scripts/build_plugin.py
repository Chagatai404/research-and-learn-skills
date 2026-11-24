"""Build a local marketplace containing one portable payload for both hosts."""
import json
import hashlib
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "research-and-learn"
MARKET = "research-and-learn-local"
SKILLS = {"learn", "research", "audit", "defend", "prepare", "manimgx", "notes-to-latex"}
DESCRIPTION = "Adaptive tutoring, reproducible research and teach-back with a shared local learner profile."


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def archive(folder, output):
    """Use stable paths, permissions, line endings and timestamps on every OS."""
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as tmp:
        staged = Path(tmp.name)
    try:
        with zipfile.ZipFile(staged, "w") as bundle:
            for source in sorted(folder.rglob("*"), key=lambda p: p.relative_to(folder).as_posix()):
                if source.is_file():
                    entry = zipfile.ZipInfo(source.relative_to(folder).as_posix())
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    bundle.writestr(entry, source.read_bytes().replace(b"\r\n", b"\n"))
        os.replace(staged, output)
    finally:
        staged.unlink(missing_ok=True)


def standalone(plugin, dest):
    support = dest / "research-and-learn-support"
    for directory in ("skills", "references", "scripts", "local", "docs"):
        shutil.copytree(plugin / directory, support / directory)
    shutil.copy2(plugin / "LICENSE", support / "LICENSE")
    for path in list(support.rglob("*.md")):
        content = path.read_text(encoding="utf-8").replace("SKILL.md)", "GUIDE.md)")
        path.write_text(content, encoding="utf-8")
        if path.name == "SKILL.md":
            path.rename(path.with_name("GUIDE.md"))
    for skill in sorted(SKILLS):
        name = f"research-and-learn-{skill}"
        guide = support / "skills" / skill / "GUIDE.md"
        _, metadata, _ = guide.read_text(encoding="utf-8").split("---", 2)
        metadata = metadata.replace(f"name: {skill}\n", f"name: {name}\n")
        entry = dest / name / "SKILL.md"
        entry.parent.mkdir()
        entry.write_text(f"---{metadata}---\n\nRead and follow the [{skill} guide]"
                         f"(../research-and-learn-support/skills/{skill}/GUIDE.md). "
                         "Use the adjacent research-and-learn-support directory as the plugin root "
                         "for helper commands. Resolve paths from this skill's installed location.\n", encoding="utf-8")


def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        market = Path(temp) / "marketplace"
        plugin = market / "plugin"
        available = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        if available != SKILLS:
            raise ValueError(f"Skill inventory differs: {available ^ SKILLS}")
        for folder in ("skills", "references", "local"):
            shutil.copytree(ROOT / folder, plugin / folder, ignore=shutil.ignore_patterns("__pycache__"))
        (plugin / "docs").mkdir()
        shutil.copy2(ROOT / "docs" / "local-ollama.md", plugin / "docs/local-ollama.md")
        helpers = plugin / "scripts"
        helpers.mkdir()
        for helper in ("profile.py", "profile_import.py", "note_edit.py"):
            shutil.copy2(ROOT / "scripts" / helper, helpers)
        shutil.copy2(ROOT / "LICENSE", plugin / "LICENSE")
        for host in (".codex-plugin", ".claude-plugin"):
            (plugin / host).mkdir()
            shutil.copy2(ROOT / host / "plugin.json", plugin / host / "plugin.json")
        write_json(market / ".agents/plugins/marketplace.json", {"name": MARKET, "plugins": [
            {"name": NAME, "source": {"source": "local", "path": "./plugin"},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]})
        write_json(market / ".claude-plugin/marketplace.json", {"name": MARKET, "owner": {"name": "Research and Learn"},
            "plugins": [{"name": NAME, "source": "./plugin", "description": DESCRIPTION}]})
        loose = Path(temp) / "skillset"
        standalone(plugin, loose)
        assets = {"research-and-learn-plugin.zip": market, "research-and-learn-skills.zip": loose}
        for filename, folder in assets.items():
            archive(folder, output / filename)
        sums = [f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}" for name in assets]
        (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="ascii")
        target = output / "marketplace"
        # Replace only this script's generated directory after a complete build.
        previous = Path(temp) / "previous"
        if target.exists():
            target.rename(previous)
        try:
            market.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise
    return target


if __name__ == "__main__":
    print(build())
