"""Serve a copy of one installed Ollama model on an independent loopback port."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / ".ollama" / "models"
DEFAULT_STORE = ROOT / "dist" / "ollama-models"
CHUNK = 4 * 1024 * 1024


def check_digest(path, expected):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(CHUNK), b""):
            digest.update(data)
    if digest.hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch in {path}")


def stage_blob(source, target, digest, size):
    if target.is_file():
        check_digest(target, digest)
        return
    if source.stat().st_size != size:
        raise ValueError(f"Unexpected file size in {source}")
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".copy-", delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        shutil.copyfile(source, staged)
        check_digest(staged, digest)
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def stage_path(store, relative):
    path = store / relative
    if path.resolve() != path:
        raise ValueError(f"A link redirects the staging path {path}")
    return path


def stage_model(source, store, model):
    if source.is_relative_to(store) or store.is_relative_to(source):
        raise ValueError("Choose a staging directory separate from the source model store")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9._-]*", model):
        raise ValueError("Use an installed Ollama library model with an explicit tag, such as qwen3:4b-instruct")
    name, tag = model.split(":")
    relative = Path("manifests/registry.ollama.ai/library") / name / tag
    manifest_bytes = (source / relative).read_bytes()
    manifest = json.loads(manifest_bytes)
    target_manifest = stage_path(store, relative)
    if target_manifest.exists() and target_manifest.read_bytes() != manifest_bytes:
        raise ValueError(f"A different manifest already exists at {target_manifest}. Choose another --store.")
    blobs = stage_path(store, "blobs")
    blobs.mkdir(parents=True, exist_ok=True)
    for layer in [manifest["config"], *manifest["layers"]]:
        digest = layer["digest"]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid model digest in {source / relative}")
        filename = digest.replace(":", "-")
        stage_blob(source / "blobs" / filename, stage_path(store, Path("blobs") / filename),
                   digest.split(":")[1], layer["size"])
    if not target_manifest.exists():
        target_manifest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target_manifest.parent, prefix=".manifest-", delete=False) as temporary:
            temporary.write(manifest_bytes)
            staged = Path(temporary.name)
        try:
            os.replace(staged, target_manifest)
        finally:
            staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:4b-instruct")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--port", type=int, default=11435)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    store = args.store.resolve()
    try:
        stage_model(args.source.resolve(), store, args.model)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Could not stage {args.model}: {exc}\n")
    print(f"Staged {args.model} in {store}", flush=True)
    if args.prepare_only:
        return 0
    ollama = shutil.which("ollama")
    if not ollama:
        parser.exit(1, "Ollama is unavailable on PATH. Start this command from a terminal with Ollama installed.\n")
    address = f"127.0.0.1:{args.port}"
    settings = {
        "OLLAMA_HOST": address, "OLLAMA_MODELS": str(store), "OLLAMA_NO_CLOUD": "1", "OLLAMA_NOPRUNE": "1",
        "OLLAMA_CONTEXT_LENGTH": "32768", "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_VULKAN": "0",
        "OLLAMA_LLM_LIBRARY": "cpu", "CUDA_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1",
        "HIP_VISIBLE_DEVICES": "-1",
    }
    print(f"Serving on http://{address}. Use http://{address}/v1 as the Codex OSS base URL.", flush=True)
    try:
        return subprocess.run([ollama, "serve"], env={**os.environ, **settings}, check=False).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
