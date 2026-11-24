# Legacy Research OS host integration

The cleanup compares the seven standalone skill directories in each host against the Research OS install manifest. An extra, missing, changed, or linked file stops the cleanup. The backup remains in the user profile on the same drive. Keep it private because the saved application configurations can contain sensitive values.

## Restore

1. Close both hosts and find the specific `legacy-hosts-*` snapshot under `%USERPROFILE%\.research-and-learn-backups` that you intend to restore. Its `restore-map.json` lists the archived skill and configuration paths relative to your home folder.
2. Check that each archived skill destination is absent. Move the corresponding directory from the snapshot to its original location. If a destination already exists, inspect both copies and reconcile them before restoring.
3. Compare the original configurations in the snapshot with the current configurations. Restore the `mcp_servers.research-os` TOML table in `.codex/config.toml`, the `mcpServers.research-os` JSON entry in `.claude.json`, and the original Research OS group in `hooks.SessionStart` in `.claude/settings.json`. Preserve settings changed since the backup.
4. Start both hosts and confirm the legacy MCP server and standalone skills appear. Claude Code should run the legacy briefing at session start.
