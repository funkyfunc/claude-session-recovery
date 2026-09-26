#!/usr/bin/env python3

"""
extract_session.py

Extracts generated artifacts, tool calls, user/assistant dialogue, subagent messages,
and safety refusal payloads from a decoded Claude session JSON file.

Usage:
  python3 extract_session.py <session.json> [--out-dir <output_directory>]
"""

import os
import sys
import json
import argparse


def extract_content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    text_parts.append(item["text"])
                elif "content" in item:
                    text_parts.append(str(item["content"]))
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts)
    return str(content) if content else ""


def main():
    parser = argparse.ArgumentParser(description="Extract artifacts and transcript from decoded session JSON.")
    parser.add_argument("session_json", help="Path to decoded session JSON file")
    parser.add_argument("--out-dir", "-o", default="./extracted_session", help="Output directory")
    args = parser.parse_args()

    with open(args.session_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = os.path.abspath(args.out_dir)
    artifacts_dir = os.path.join(out_dir, "artifacts")
    logs_dir = os.path.join(out_dir, "logs")

    os.makedirs(artifacts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    events = data.get("tree", {}).get("events", [])
    if not events and "events" in data:
        events = data["events"]

    print(f"[INFO] Processing {len(events)} events from {args.session_json}...")

    transcript_lines = []
    written_files = 0
    commands_run = 0
    searches = []
    safety_errors = []
    subagent_calls = []

    conv_uuid = data.get("conversationUuid", "unknown")
    transcript_lines.append(f"# Session Transcript: {conv_uuid}\n")

    for ev in events:
        seq = ev.get("seq", "unknown")
        kind = ev.get("kind", "")
        payload = ev.get("payload", {})
        msg = payload.get("message", {})

        role = msg.get("role") or msg.get("sender") or msg.get("author") or payload.get("type")
        content_obj = msg.get("content", [])

        # Check for tool_use in content
        if isinstance(content_obj, list):
            for part in content_obj:
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    tool_name = part.get("name", "")
                    tool_input = part.get("input", {})

                    # File Write Tool
                    if tool_name in ["Write", "write_file", "write_to_file"]:
                        file_path = tool_input.get("path") or tool_input.get("TargetFile") or tool_input.get("file_path")
                        file_content = tool_input.get("content") or tool_input.get("CodeContent") or ""
                        if file_path and file_content:
                            # Sanitize filename
                            rel_name = os.path.basename(file_path)
                            dest_path = os.path.join(artifacts_dir, rel_name)
                            with open(dest_path, "w", encoding="utf-8") as af:
                                af.write(file_content)
                            written_files += 1
                            transcript_lines.append(f"\n> **[Seq {seq}] Tool Use: `{tool_name}` -> `{rel_name}`**\n")

                    # Command Execution
                    elif tool_name in ["Bash", "bash", "run_command"]:
                        cmd_line = tool_input.get("command") or tool_input.get("CommandLine")
                        commands_run += 1
                        transcript_lines.append(f"\n```bash\n# [Seq {seq}] Command:\n{cmd_line}\n```\n")

                    # Web Search
                    elif "search" in tool_name.lower():
                        q = tool_input.get("query")
                        if q:
                            searches.append({"seq": seq, "query": q})

                    # Subagent invocation
                    elif tool_name in ["SendMessage", "invoke_subagent"]:
                        subagent_calls.append({"seq": seq, "tool": tool_name, "input": tool_input})

        # Check for safety filter errors or refusals
        text_str = extract_content_text(content_obj)
        if "reasoning_extraction" in text_str or "api_refusal_category" in text_str or "safeguards flagged" in text_str:
            safety_errors.append({"seq": seq, "text": text_str[:1000]})

        # Format transcript entry
        if text_str.strip():
            transcript_lines.append(f"### [Seq {seq}] {str(role).upper()}:\n")
            transcript_lines.append(text_str.strip())
            transcript_lines.append("\n---\n")

    # Save Transcript
    transcript_path = os.path.join(out_dir, "transcript.md")
    with open(transcript_path, "w", encoding="utf-8") as tf:
        tf.write("\n".join(transcript_lines))

    # Save Logs
    if safety_errors:
        with open(os.path.join(logs_dir, "safety_refusals.json"), "w", encoding="utf-8") as ef:
            json.dump(safety_errors, ef, indent=2)

    if searches:
        with open(os.path.join(logs_dir, "web_searches.json"), "w", encoding="utf-8") as sf:
            json.dump(searches, sf, indent=2)

    if subagent_calls:
        with open(os.path.join(logs_dir, "subagent_calls.json"), "w", encoding="utf-8") as subf:
            json.dump(subagent_calls, subf, indent=2)

    print(f"\n[SUMMARY] Extraction complete:")
    print(f"  Output Directory:     {out_dir}")
    print(f"  Artifacts Saved:      {written_files} files -> {artifacts_dir}")
    print(f"  Transcript:           {transcript_path}")
    print(f"  Commands Run Logged:  {commands_run}")
    print(f"  Web Searches Logged:  {len(searches)}")
    print(f"  Safety Refusals:      {len(safety_errors)}")


if __name__ == "__main__":
    main()
