# Research and Learn

Study a course or an independent subject, investigate a research question, or learn how an agent produced a result. Codex, Claude Code and tool-capable local-model hosts use the same seven skill files. The assistant tutors in chat and in your Obsidian notes. A local learner profile makes the next question depend on your previous answers.

## Start

- **Learn** — “Continue CENG487 from my last unanswered question. Give me one problem and let me answer in the lecture note.”
- **Prepare** — “Prepare the next syllabus week. Connect the definitions, worked examples, derivation and practice to my course index.”
- **Research** — “Investigate this question. Find the primary papers, verify the consequential claims and test the strongest alternative explanation.”
- **Audit** — “Independently check whether this result supports this claim.”
- **Defend** — “Walk me through the code that produced this figure, then have me reconstruct the argument.”
- **Notes to LaTeX** — “Transcribe this page of my handwritten derivation faithfully.”
- **ManimGX** — “Show how this projection changes as the basis rotates.”

Use the namespaced skill when older skills with the same names are installed. In Claude Code, for example, invoke `/research-and-learn:learn`. In Codex, select the plugin's Learn skill from the skill picker. For existing material, provide the vault path and course or research index on first use. Keep prompts and feedback in the current week or topic. A new chat can resume an unanswered question.

## Build and install

With Python 3.12 or later and the host CLI installed, run these commands from the project directory. Build creates a local marketplace containing the shared runtime. Private notes, learner data and migration backups stay outside the installable package.

```powershell
python scripts/build_plugin.py
codex plugin marketplace add ./dist/marketplace
codex plugin add research-and-learn@research-and-learn-local
claude plugin marketplace add ./dist/marketplace
claude plugin install research-and-learn@research-and-learn-local
```

Start a new host session to discover installed skills. To inspect a build in Claude Code before installing it, use `claude --plugin-dir ./dist/marketplace/plugin`. To use Ollama through Codex, run `codex --oss --local-provider ollama -m MODEL_TAG` with an installed model that supports the host's tools. Select the same plugin skill. Local models need working file and command tools for persistence. Source verification also needs a host with research tools and access to the source. An outstanding research pass can continue on another host.

## Local state and note editing

For the installed Qwen model on this machine, see the [local Ollama setup](docs/local-ollama.md). It uses the existing model files and the same Codex plugin.

Run `python scripts/profile.py --help` for the supported profile operations. Use a disposable profile for demonstrations. A missing grade is unknown. A claim decision, reading history, or a research agent's successful experiment cannot establish a learner's mastery.

For a note edit, save the proposed full text to a local draft, then run `python scripts/note_edit.py preview VAULT RELATIVE_NOTE DRAFT`. Inspect the diff, preserve unrelated edits, and apply the same draft with `apply`, `--expect` and `--draft-hash`. The helper backs up prior bytes outside the vault, checks the current digest and reads back the result. Use another preview to restore a backed-up version. The per-note lock coordinates plugin writers. Close competing active editors during bulk migrations.

The migration tooling and backup manifests are separate from the teaching plugin. Keep local migration records private. See the [vault migration and restore guide](migration/VAULT.md), the [legacy host restore guide](migration/legacy_hosts.md), and the [design and acceptance criteria](.plans/research-and-learning-spec.md).
