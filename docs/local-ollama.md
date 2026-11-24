# Use Ollama with the installed Codex plugin

The examples use PowerShell on Windows and assume Ollama, Codex CLI, Python 3.12 or newer, and the Research and Learn plugin are installed. Start from the repository root. The default model is the existing `qwen3:4b-instruct` tag.

## Start an isolated local server

Run this in one terminal and leave it open while you use Codex.

```powershell
python local/ollama.py
```

The launcher copies the selected model's manifest and blobs from `$HOME/.ollama/models` to the ignored `dist/ollama-models` directory. It verifies each blob against its SHA-256 digest in the manifest and reuses the staged copy on later launches. The default model uses approximately 2.5 GB of disk space. Ollama listens on `127.0.0.1:11435` with cloud features disabled. The launcher uses CPU inference to work around the CUDA timeout seen on this machine.

Use `--source` for a different installed model store, `--model` for another installed library tag, or `--port` if 11435 is occupied. Press Ctrl+C in the server terminal to stop it.

## Open Codex with the model

In a second terminal, set the endpoint for this shell and confirm Ollama sees the model before launching Codex.

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:CODEX_OSS_BASE_URL = 'http://127.0.0.1:11435/v1'
ollama list
codex --oss --local-provider ollama -m qwen3:4b-instruct -c model_context_window=32768
```

If you chose another port or model, use it in both sets of commands. `CODEX_OSS_BASE_URL` selects the inference endpoint Codex uses. Start a new chat and select the installed Learn skill. A small test is “Use the Research and Learn plugin to help me learn the chain rule for differentiation. Ask me one diagnostic question.” If testing persistence, set `RESEARCH_LEARN_PROFILE` to a disposable SQLite path before opening Codex.

The local smoke verified that Codex can call Ollama and receive shell tool calls from Qwen. The model supplied an invalid shell working directory during the test, so it did not save or reopen the diagnostic question.

For literature work, verify that the selected host exposes a working public-source search or browser. Hand off outstanding source verification to an equipped host when necessary.
