#!/usr/bin/env bash

# recover.sh
# End-to-end recovery pipeline for Claude Desktop & Cowork sessions.
#
# Usage:
#   ./recover.sh [session_id_or_query] [output_directory]

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
QUERY="${1:-cse_}"
OUT_DIR="${2:-./recovered_session}"

echo "=========================================================="
echo " Claude Session & Artifact Recovery Tool"
echo "=========================================================="
echo "Target Query:     $QUERY"
echo "Output Directory: $OUT_DIR"
echo ""

mkdir -p "$OUT_DIR"

# 1. Scan for matching blob
echo "[1/4] Scanning IndexedDB stores..."
MATCH_JSON=$(python3 "$DIR/scan_sessions.py" -q "$QUERY" --json)

BLOB_PATH=$(echo "$MATCH_JSON" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    if data and len(data) > 0:
        print(data[0]["blob_path"])
except Exception:
    pass
')

if [ -z "$BLOB_PATH" ]; then
    echo "[!] No matching IndexedDB blob found for: $QUERY"
    echo "    Available sessions:"
    python3 "$DIR/scan_sessions.py"
    exit 1
fi

echo "[+] Found matching blob: $BLOB_PATH"

# 2. Decompress and Deserialize
echo ""
echo "[2/4] Decompressing Snappy & deserializing V8 payload..."
JSON_OUT="$OUT_DIR/raw_session.json"
node "$DIR/decompress_blob.js" "$BLOB_PATH" "$JSON_OUT"

# 3. Extract Session Artifacts & Transcript
echo ""
echo "[3/4] Extracting artifacts, code, and dialogue..."
python3 "$DIR/extract_session.py" "$JSON_OUT" --out-dir "$OUT_DIR"

# 4. Check for DOM snapshot in Downloads
echo ""
echo "[4/4] Checking ~/Downloads for matching DOM HTML exports..."
MATCH_HTML=$(find "$HOME/Downloads" -maxdepth 1 -name "*Claude*.html" 2>/dev/null | head -n 1 || true)
if [ -n "$MATCH_HTML" ]; then
    echo "[+] Found DOM snapshot: $MATCH_HTML"
    python3 "$DIR/parse_dom_html.py" "$MATCH_HTML" --out "$OUT_DIR/dom_snapshot.md"
else
    echo "[-] No local HTML DOM snapshot found in ~/Downloads (skipping)."
fi

echo ""
echo "=========================================================="
echo " Recovery complete! All files saved to:"
echo " $OUT_DIR"
echo "=========================================================="
ls -la "$OUT_DIR"
