# Claude Session Recovery Toolkit & Skill

A fast, automated toolkit and agent skill for recovering, decompressing, and reconstructing Claude Desktop (Electron) and Google Chrome sessions on macOS.

## Why This Exists

When working on complex agentic tasks with Claude Cowork or Claude Desktop, sessions can occasionally freeze, disconnect, or trigger safety filter halts (such as false-positive `reasoning_extraction` flags). 

Recovering these sessions from disk is notoriously difficult because:
1. **Google Snappy Compression:** Modern Chromium (Chrome 129+) compresses external IndexedDB blobs using Snappy, making plain `grep`, `mdfind`, and `strings` completely useless.
2. **V8 Binary Serialization:** The uncompressed payload is encoded as a V8 `SerializedScriptValue` object (`0xff 0x11` / `0x10`), incompatible with standard Node.js without version byte patching.
3. **Cowork Sliding Windows:** Long-running Cowork sessions maintain a 100-event rolling sliding window locally (`floorSeq` to `headSeq`), requiring triangulation across blobs, HTTP caches, and DOM exports.

This toolkit solves all of these problems with a single command.

---

## Quick Start

### One-Command Recovery:
```bash
./scripts/recover.sh "cse_01ULs3qBKsrAjJuxWeCovBgh" ./my_recovered_session
```

### Scan Available Sessions:
```bash
python3 scripts/scan_sessions.py
```

### Decompress a Specific Blob:
```bash
node scripts/decompress_blob.js "/path/to/blob" output.json
```

### Extract Artifacts & Transcript:
```bash
python3 scripts/extract_session.py output.json --out-dir ./extracted
```

---

## Repository Structure

- [`SKILL.md`](./SKILL.md) — The AI agent skill specification.
- [`scripts/recover.sh`](./scripts/recover.sh) — End-to-end recovery script.
- [`scripts/scan_sessions.py`](./scripts/scan_sessions.py) — Scanner for IndexedDB blobs across Claude Desktop & Chrome.
- [`scripts/decompress_blob.js`](./scripts/decompress_blob.js) — Snappy decompressor and V8 version-patching deserializer.
- [`scripts/extract_session.py`](./scripts/extract_session.py) — Artifact, command, and dialogue extractor.
- [`scripts/parse_dom_html.py`](./scripts/parse_dom_html.py) — HTML DOM snapshot parser.
- [`references/claude_storage_architecture.md`](./references/claude_storage_architecture.md) — Technical deep-dive on macOS storage mechanisms.
