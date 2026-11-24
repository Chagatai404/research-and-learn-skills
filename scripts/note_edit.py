"""Preview and apply a single recoverable UTF-8 Markdown edit in a vault."""
import argparse
import difflib
import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


def digest(content):
    return "new" if content is None else hashlib.sha256(content).hexdigest()


def note_path(root, relative):
    root = root.resolve(strict=True)
    if not root.is_dir() or relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError("Use a relative note path inside an existing vault")
    if relative.suffix.lower() != ".md" or any(p.startswith(".") or ":" in p for p in relative.parts):
        raise ValueError("Select a visible Markdown note")
    path = root.joinpath(relative)
    node = path
    while node != root:
        if node.is_symlink() or (node.exists() and getattr(node.lstat(), "st_file_attributes", 0) &
                                  getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)):
            raise ValueError("Linked note paths are unsupported")
        node = node.parent
    path.resolve().relative_to(root)
    return path


def contents(path):
    return path.read_bytes() if path.exists() else None


@contextmanager
def note_lock(path):
    lock = path.with_name("." + path.name + ".research-and-learn.lock")
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def apply(path, proposed, expected, backup_dir):
    with note_lock(path):
        before = contents(path)
        if digest(before) != expected:
            raise ValueError("Note changed. Read it and preview a new edit.")
        if before == proposed:
            return
        if before is not None:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / (digest(before) + ".md")
            if not backup.exists():
                try:
                    with backup.open("xb") as handle:
                        handle.write(before)
                except FileExistsError:
                    pass
            if backup.read_bytes() != before:
                raise ValueError("Backup verification failed")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(proposed)
        try:
            if digest(contents(path)) != expected:
                raise ValueError("Concurrent edit detected")
            if before is None and os.name == "nt":
                os.rename(temporary, path)
            elif before is None:
                os.link(temporary, path)
            else:
                os.replace(temporary, path)
            if contents(path) != proposed:
                raise ValueError("Written note differs from the preview")
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preview", "apply"])
    parser.add_argument("vault", type=Path)
    parser.add_argument("note", type=Path, help="Vault-relative note in an existing directory")
    parser.add_argument("draft", type=Path, help="Local UTF-8 file holding proposed note contents")
    parser.add_argument("--expect", help="Original digest from preview, or new")
    parser.add_argument("--draft-hash", help="Proposed digest from preview")
    parser.add_argument("--backups", type=Path, default=Path.home() / ".research-and-learn" / "note-backups")
    args = parser.parse_args()
    try:
        path = note_path(args.vault, args.note)
        before, proposed = contents(path), args.draft.read_bytes()
        lines = proposed.decode("utf-8-sig").splitlines(keepends=True)
        if args.action == "preview":
            original = (before or b"").decode("utf-8-sig").splitlines(keepends=True)
            print("".join(difflib.unified_diff(original, lines, "current", "proposed")))
            print("Original", digest(before), "Proposed", digest(proposed))
        else:
            if args.draft_hash != digest(proposed):
                raise ValueError("Supply the proposed digest from preview")
            apply(path, proposed, args.expect, args.backups)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
