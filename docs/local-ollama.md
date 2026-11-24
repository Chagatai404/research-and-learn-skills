# Use Ollama with the installed Codex plugin

The examples use PowerShell on Windows and assume Ollama, Codex CLI, Python 3.12 or newer, and the Research and Learn plugin are installed. Start from the repository root. The default model is the existing `qwen3:4b-instruct` tag.

## Start an isolated local server

Run this from the repository root in one terminal and leave it open while you use Codex.

```powershell
$workspace = (Get-Location).Path
python local/ollama.py --workspace $workspace
```

The launcher copies the selected model's manifest and blobs from `$HOME/.ollama/models` to the ignored `dist/ollama-models` directory. It verifies each blob against its SHA-256 digest in the manifest and reuses the staged copy on later launches. The default model uses approximately 2.5 GB of disk space. Ollama listens on `127.0.0.1:11435` with cloud features disabled. With `--workspace`, the launcher also listens on `127.0.0.1:11436` for Codex requests for that workspace. The launcher uses CPU inference to work around the CUDA timeout seen on this machine.

Use `--source` for a different installed model store, `--model` for another installed library tag, `--port` to change the Ollama port, or `--codex-port` to change the Codex endpoint port. Press Ctrl+C in the server terminal to stop both listeners.

## Open Codex with the model

Open a second terminal in the same repository. Set the endpoints and confirm Ollama sees the model before launching Codex.

```powershell
$workspace = (Get-Location).Path
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:CODEX_OSS_BASE_URL = 'http://127.0.0.1:11436/v1'
ollama list
codex --oss --local-provider ollama -m qwen3:4b-instruct -c model_context_window=32768 --cd $workspace
```

Use the same directory for `--workspace` and `--cd`. If you changed either port or the model tag, use the same value in both terminals. Start a new chat and select the installed Learn skill. A small test is “Use the Research and Learn plugin to help me learn the chain rule for differentiation. Ask me one diagnostic question.” If testing persistence, set `RESEARCH_LEARN_PROFILE` to a disposable SQLite path before opening Codex.

Qwen previously sent `C:\workspace` as the shell working directory even though the repository was elsewhere. The Codex endpoint replaces that placeholder with the selected workspace when the path is missing. Codex still applies the session's normal sandbox and approval settings to the shell call. The Learn persistence smoke still needs to be rerun through this endpoint.

For literature work, verify that the selected host exposes a working public-source search or browser. Hand off outstanding source verification to an equipped host when necessary.
