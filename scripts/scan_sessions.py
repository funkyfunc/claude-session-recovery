#!/usr/bin/env python3

"""
scan_sessions.py

Scans macOS Claude Desktop and Google Chrome IndexedDB stores to locate
active and archived Claude conversations, Cowork sessions, and blobs.

Usage:
  python3 scan_sessions.py [--query <filter>] [--json]
"""

import os
import sys
import json
import subprocess
import argparse

CLAUDE_INDEXEDDB = os.path.expanduser(
    "~/Library/Application Support/Claude/IndexedDB/https_claude.ai_0.indexeddb.blob"
)
CHROME_INDEXEDDB = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/IndexedDB/https_claude.ai_0.indexeddb.blob"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DECOMPRESS_JS = os.path.join(SCRIPT_DIR, "decompress_blob.js")


def find_all_blobs():
    blob_paths = []
    for base in [CLAUDE_INDEXEDDB, CHROME_INDEXEDDB]:
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if not f.startswith("."):
                    blob_paths.append(os.path.join(root, f))
    return sorted(blob_paths, key=lambda p: os.path.getmtime(p), reverse=True)


def probe_blob(blob_path):
    cmd = ["node", DECOMPRESS_JS, blob_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return None
        # Parse stdout JSON
        output = proc.stdout
        # Find where JSON starts
        start_idx = output.find("{")
        if start_idx == -1:
            return None
        data = json.loads(output[start_idx:])
        return data
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Scan Claude Desktop & Chrome IndexedDB for sessions.")
    parser.add_argument("--query", "-q", help="Filter by session ID, UUID, or conversation name")
    parser.add_argument("--json", action="store_true", help="Output raw JSON array")
    args = parser.parse_args()

    blobs = find_all_blobs()
    print(f"[INFO] Discovered {len(blobs)} IndexedDB blobs across Claude and Chrome.", file=sys.stderr)

    results = []
    for b in blobs:
        data = probe_blob(b)
        if not data:
            continue

        conv_uuid = data.get("conversationUuid", "")
        name = data.get("name", "")
        product = data.get("product", "")
        msg_count = data.get("messageCount", 0)
        tree = data.get("tree", {})
        floor_seq = tree.get("floorSeq", "")
        head_seq = tree.get("headSeq", "")
        events_len = len(tree.get("events", [])) if isinstance(tree.get("events"), list) else 0

        # Query filter
        if args.query:
            q = args.query.lower()
            match = (
                q in conv_uuid.lower() or
                q in str(name).lower() or
                q in product.lower() or
                q in b.lower()
            )
            if not match:
                continue

        results.append({
            "blob_path": b,
            "conversation_uuid": conv_uuid,
            "name": name,
            "product": product,
            "message_count": msg_count,
            "floor_seq": floor_seq,
            "head_seq": head_seq,
            "events_count": events_len,
            "modified_time": os.path.getmtime(b)
        })

    if args.json:
        print(json.dumps(results, indent=2))
        return

    if not results:
        print("No matching sessions found.")
        return

    # Print Table
    print(f"\n{'UUID / Session ID':<36} | {'Product':<8} | {'Msgs':<4} | {'Seq Range':<11} | {'Blob File':<12}")
    print("-" * 80)
    for r in results:
        uuid_str = r['conversation_uuid'][:36]
        seq_range = f"{r['floor_seq']}..{r['head_seq']}" if r['floor_seq'] else f"{r['events_count']} ev"
        blob_base = os.path.basename(r['blob_path'])
        print(f"{uuid_str:<36} | {r['product']:<8} | {r['message_count']:<4} | {seq_range:<11} | {blob_base:<12}")


if __name__ == "__main__":
    main()
