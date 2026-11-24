"""Build a local marketplace containing one portable payload for both hosts."""
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "research-and-learn"
MARKET = "research-and-learn-local"
SKILLS = {"learn", "research", "audit", "defend", "prepare", "manimgx", "notes-to-latex"}
DESCRIPTION = "Adaptive tutoring, reproducible research and teach-back with a shared local learner profile."


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        market = Path(temp) / "marketplace"
        plugin = market / "plugin"
        available = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        if available != SKILLS:
            raise ValueError(f"Skill inventory differs: {available ^ SKILLS}")
        for folder in ("skills", "references"):
            shutil.copytree(ROOT / folder, plugin / folder, ignore=shutil.ignore_patterns("__pycache__"))
        helpers = plugin / "scripts"
        helpers.mkdir()
        for source in (ROOT / "scripts").glob("*.py"):
            if source.name != "build_plugin.py":
                shutil.copy2(source, helpers)
        if not (helpers / "profile.py").is_file():
            raise ValueError("Missing learner profile helper")
        manifest = {"name": NAME, "version": "1.0.2", "description": DESCRIPTION}
        shutil.copy2(ROOT / "LICENSE", plugin / "LICENSE")
        write_json(plugin / ".codex-plugin/plugin.json", {**manifest, "skills": "./skills/"})
        write_json(plugin / ".claude-plugin/plugin.json", manifest)
        write_json(market / ".agents/plugins/marketplace.json", {"name": MARKET, "plugins": [
            {"name": NAME, "source": {"source": "local", "path": "./plugin"},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]})
        write_json(market / ".claude-plugin/marketplace.json", {"name": MARKET, "owner": {"name": "Research and Learn"},
            "plugins": [{"name": NAME, "source": "./plugin", "description": DESCRIPTION}]})
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
