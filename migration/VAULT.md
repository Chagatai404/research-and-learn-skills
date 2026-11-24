# Vault migration and restore

Open `Home.md` → `Study and Research` in `C:/Users/ASUS/Obsidian/Knowledge`. The pilot covers CENG487. The remaining batch adds the other course, research and library indexes. Cleanup marks the former app as retired, qualifies four Home links to their curated notes, removes the former portal footer and metadata from the seven question notes embedded in active investigations, and indexes seven review snapshots dated 2026-11-24.

## Reconciliation

| Check | Result |
| --- | ---: |
| Originals with exactly one mapped section | 521 |
| Course, research and library originals | 157 / 129 / 235 |
| Markdown files created / modified | 34 / 40 |
| Final file hashes checked | 557 |
| Introduced Obsidian links resolved | 698 |
| Inherited missing or ambiguous link occurrences | 294 |

The inherited links occur in 75 notes. The two notes for one unidentified course remain under `Material to identify`. CENG487 follows the supplied lecture order, with Lecture 7 identified as a reconstruction and calendar weeks undocumented. The STAT303 index follows documented topics because the provenance of the expanded 14-week plan is unclear. Historic app exports retain their original portal references outside the seven embedded question notes. The app-generated `Research OS/Knowledge/Knowledge.md` changed after the initial snapshot. The cleanup manifest records both hashes and preserves the newer file.

The private artifacts are in `D:/Projects/research-and-learn-skills/.migration/verified`. Use `pilot`, `remaining` and `cleanup`. Each folder contains the sealed `manifest.json`, byte-for-byte originals under `before`, staged output under `after`, and `inherited-links.json`. `final-check.json` contains the aggregate reconciliation and inherited-link list. The first cleanup was rolled back before applying the Home-link revision. Its original sealed artifacts remain under `superseded-cleanup-first-applied`. Preserve the private artifacts locally for restoration.

From `D:/Projects/research-and-learn-skills`, verify the current state with:

```powershell
python migration/vault.py reconcile --work .migration/verified
```

Each batch passed a restore drill. A second drill copied the final changed notes into a temporary directory, restored all three batches in reverse order, and reapplied them in forward order. Both sets of file hashes matched.

## Restore

To undo only the cleanup, run the first command. To restore all migration writes, run all three in the order shown. Run from `D:/Projects/research-and-learn-skills` with write access to the vault. A preflight checks file hashes and stops if a note has changed since the migration. Keep such edits and review the corresponding `before` and `after` copies before merging. Generated directories may remain empty after restore.

```powershell
python migration/vault.py restore cleanup --work .migration/verified
python migration/vault.py restore remaining --work .migration/verified
python migration/vault.py restore pilot --work .migration/verified
```

The seven review snapshots and the refreshed Knowledge index were generated outside this migration. They remain in the vault after restoring the migration writes.
