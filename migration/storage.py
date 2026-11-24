"""Checked, reversible Markdown edits. All paths in manifests are relative to the vault."""
import hashlib
import json
import os
import tempfile
from pathlib import Path, PureWindowsPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(root, name):
    if not name or PureWindowsPath(name).anchor or any(x in ('..', '.') for x in Path(name).parts):
        raise ValueError(f'Unsafe relative path: {name}')
    target = root / name
    if not target.resolve().is_relative_to(root.resolve()) or any(
        p.is_symlink() or p.is_junction() for p in (target, *target.parents) if p.is_relative_to(root)
    ):
        raise ValueError(f'Path escapes the migration root: {name}')
    return target


def current(path):
    return digest(path.read_bytes()) if path.is_file() else None


def swap(path, data, expected):
    if current(path) != expected:
        raise ValueError(f'Concurrent edit at {path}')
    if data is None:
        path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if current(path) != expected:
            raise ValueError(f'Concurrent edit at {path}')
        if expected is None:
            # Creating an existing name fails atomically.
            if os.name == 'nt':
                os.rename(temp, path)
            else:
                os.link(temp, path)
        else:
            os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def transfer(vault, batch, reverse=False):
    changes = json.loads((batch/'manifest.json').read_text(encoding='utf8'))['changes']
    src, dst = ('after','before') if reverse else ('before','after')
    pending = []
    for entry in changes:
        path = checked(vault, entry['path'])
        if path.suffix.lower() != '.md':
            raise ValueError(f'Unsupported destination {path}')
        result = current(path)
        if result == entry[dst]:
            continue
        if result != entry[src]:
            raise ValueError(f'Concurrent edit requires reconciliation: {path}')
        data = None
        if entry[dst] is not None:
            data = checked(batch/dst, entry['path']).read_bytes()
            if digest(data) != entry[dst]:
                raise ValueError(f'Corrupt {dst} backup: {path}')
        pending.append((path, data, entry[src], entry[dst]))
    for path, data, expected, target in pending:
        swap(path, data, expected)
        if current(path) != target:
            raise ValueError(f'Read-back mismatch: {path}')


def restore_drill(batch, changes):
    with tempfile.TemporaryDirectory(prefix='restore-', dir=batch) as tmp:
        replica = Path(tmp)
        for entry in changes:
            if entry['before'] is not None:
                name = entry['path']
                file = checked(replica, name)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(checked(batch/'before',name).read_bytes())
        transfer(replica, batch)
        transfer(replica, batch)  # recovery after interrupted/replayed apply
        transfer(replica, batch, reverse=True)
        for entry in changes:
            if current(checked(replica, entry['path'])) != entry['before']:
                raise ValueError(f'Restore failed: {entry["path"]}')

