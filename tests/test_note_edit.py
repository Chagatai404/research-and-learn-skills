import tempfile
import unittest
from pathlib import Path

from scripts.note_edit import apply, digest, note_path


class NoteEditTest(unittest.TestCase):
    def test_backup_restore_preserves_original_bytes_and_rejects_stale_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = note_path(root, Path("Week 1.md"))
            backups = root / "backups"
            before = b"Original\r\n"
            apply(note, before, "new", backups)
            after = b"Original\r\nAnswer\r\n"
            apply(note, after, digest(before), backups)
            with self.assertRaises(ValueError):
                apply(note, b"Late edit", digest(before), backups)
            self.assertEqual(note.read_bytes(), after)
            restored = (backups / (digest(before) + ".md")).read_bytes()
            apply(note, restored, digest(after), backups)
            self.assertEqual(note.read_bytes(), before)

    def test_outside_or_hidden_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ["../other.md", ".obsidian/config.md", "other.pdf"]:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    note_path(Path(directory), Path(name))
