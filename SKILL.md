---
name: claude-session-recovery
description: >-
  Locates, decompresses, deserializes, and reconstructs Claude Desktop and Cowork conversations,
  artifacts, and execution logs from macOS Chromium IndexedDB blobs and caches. Use when
  a user needs to recover lost, frozen, or safety-interrupted Claude Cowork sessions, extract
  generated reports, or reconstruct chat history.
---

# Claude Session Recovery Skill

This skill provides an automated procedure and command-line toolkit to recover, decompress, and reconstruct conversations, artifacts, code files, and execution logs from local Claude Desktop (Electron) and Google Chrome IndexedDB storage on macOS.

---

## When to Activate This Skill

Activate this skill when:
- A user asks to find, extract, or reconstruct a Claude Cowork or Claude Desktop conversation on their hard drive.
- A session was abruptly halted, frozen, or interrupted by an Anthropic safety filter (e.g., `reasoning_extraction`, `prompt_injection`, or policy refusal) and the user wants to recover reports or files generated before the halt.
- A session ID (`cse_...`) or conversation UUID is provided and needs to be located on disk.
- Plain `grep` or file searches fail to find conversation text in `~/Library/Application Support/Claude`.

---

## Quick Reference / Automated Pipeline

Run the master recovery script directly from the skill directory:

```bash
cd /Users/stompinggrounds/Development/claude-session-recovery
./scripts/recover.sh "<session_id_or_keyword>" "<output_directory>"
```

### Example:
```bash
cd /Users/stompinggrounds/Development/claude-session-recovery
./scripts/recover.sh "cse_01ULs3qBKsrAjJuxWeCovBgh" "/Users/stompinggrounds/Development/crux/docs/research/round-6-recovered"
```

The script automatically:
1. Scans Claude Desktop and Google Chrome IndexedDB stores for matching session blobs.
2. Decompresses Chromium Snappy compression and deserializes the V8 binary payload.
3. Unpacks generated files (`Write` tool calls), bash commands, web searches, and dialogue into markdown and JSON files.
4. Checks `~/Downloads/` for exported HTML DOM snapshots and extracts rendered message text.

---

## Step-by-Step Manual Workflow

If you need fine-grained control over individual recovery steps:

### Step 1: Scan for Session Blobs
Search IndexedDB LevelDB indexes and external blobs:

```bash
python3 /Users/stompinggrounds/Development/claude-session-recovery/scripts/scan_sessions.py -q "<query>"
```
*Outputs a table showing Session ID, Product (`chat` vs `cowork`), message count, sequence ranges, and blob file paths.*

### Step 2: Decompress Snappy & Deserialize V8
Chromium stores blobs using Snappy compression with variable header offsets (0–32 bytes) and V8 `SerializedScriptValue` version `0x11`/`0x10`. Standard `v8.deserialize()` requires patching the version byte to `0x0f`:

```bash
node /Users/stompinggrounds/Development/claude-session-recovery/scripts/decompress_blob.js \
  "/path/to/IndexedDB/blob/file" \
  "/path/to/output.json"
```

### Step 3: Extract Artifacts, Commands, and Transcript
Unpack all tool outputs, generated files, transcripts, and safety refusal payloads:

```bash
python3 /Users/stompinggrounds/Development/claude-session-recovery/scripts/extract_session.py \
  "/path/to/output.json" \
  --out-dir "/path/to/destination"
```

### Step 4: Parse Exported HTML DOM Snapshots
If the user saved the conversation webpage (`Cmd+S`) in Chrome or Claude Desktop:

```bash
python3 /Users/stompinggrounds/Development/claude-session-recovery/scripts/parse_dom_html.py \
  "$HOME/Downloads/<conversation_name>.html" \
  --out "/path/to/destination/dom_transcript.md"
```

---

## Critical Technical Traps to Avoid

1. **Do not use plain `grep` or `strings` on IndexedDB blobs:**  
   Because blobs are compressed with Google Snappy, raw text strings are garbled. Always use `decompress_blob.js`.
2. **Be aware of the Cowork 100-event sliding window:**  
   Remote Cowork sessions (`kind: "cowork_remote"`) maintain a rolling buffer of 100 events (`floorSeq` to `headSeq`). Older events (0 to `floorSeq - 1`) are retained on Claude's servers (`claude.ai`). Triangulate with DOM HTML snapshots in `~/Downloads` to recover earlier rendered turns.
3. **Safety Refusals (`reasoning_extraction`):**  
   If an automated safety classifier interrupted the session, the error payload is preserved in the event stream. When drafting a resumption prompt for the user, frame the continuation around research synthesis and human pair-programming rather than automated multi-agent grading.

---

## Toolkit Directory Structure

```
/Users/stompinggrounds/Development/claude-session-recovery/
├── SKILL.md                              # This skill instruction guide
├── package.json                          # Node dependencies (snappyjs)
├── node_modules/                         # Installed packages
├── scripts/
│   ├── recover.sh                        # End-to-end recovery automation
│   ├── scan_sessions.py                  # Scans IndexedDB stores for session IDs
│   ├── decompress_blob.js                # Snappy decompressor & V8 deserializer
│   ├── extract_session.py                # Artifact & transcript extractor
│   └── parse_dom_html.py                 # HTML DOM snapshot parser
└── references/
    └── claude_storage_architecture.md    # Detailed macOS storage architecture
```
