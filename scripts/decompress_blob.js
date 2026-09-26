#!/usr/bin/env node

/**
 * decompress_blob.js
 * 
 * Automatically decompresses Chromium Snappy-compressed IndexedDB external blobs
 * and deserializes V8 SerializedScriptValue payloads.
 * 
 * Handles:
 * - Variable-length Chromium blob headers (0–32 bytes)
 * - Snappy compression framing
 * - 15-byte Chromium IndexedDB::SerializedScriptValue prefix
 * - V8 version byte header patching (0x11/0x10 -> 0x0f)
 * 
 * Usage:
 *   node decompress_blob.js <blob_path> [output_json_path]
 */

const fs = require('fs');
const path = require('path');
const v8 = require('v8');

let snappy;
try {
  snappy = require(path.join(__dirname, '../node_modules/snappyjs'));
} catch (e) {
  try {
    snappy = require('snappyjs');
  } catch (err) {
    console.error('[ERROR] snappyjs not found. Run: npm install in skill directory.');
    process.exit(1);
  }
}

function decodeBlob(buf) {
  // Strategy A: Snappy compressed with header offset
  for (let off = 0; off <= 32; off++) {
    let unc;
    try {
      unc = snappy.uncompress(buf.subarray(off));
    } catch (e) {
      continue;
    }

    // Inside uncompressed payload, scan for V8 header (0xff)
    for (let v8off = 0; v8off <= 32; v8off++) {
      if (v8off >= unc.length) break;
      if (unc[v8off] === 0xff) {
        for (const targetVer of [0x0f, 0x10, 0x0e, 0x0d]) {
          try {
            const copy = Buffer.from(unc.subarray(v8off));
            copy[1] = targetVer;
            const obj = v8.deserialize(copy);
            if (obj && typeof obj === 'object') {
              return {
                data: obj,
                snappyOffset: off,
                v8Offset: v8off,
                version: targetVer,
                compressed: true
              };
            }
          } catch (e) {}
        }
      }
    }
  }

  // Strategy B: Raw uncompressed payload with header offset
  for (let v8off = 0; v8off <= 32; v8off++) {
    if (v8off >= buf.length) break;
    if (buf[v8off] === 0xff) {
      for (const targetVer of [0x0f, 0x10, 0x0e, 0x0d]) {
        try {
          const copy = Buffer.from(buf.subarray(v8off));
          copy[1] = targetVer;
          const obj = v8.deserialize(copy);
          if (obj && typeof obj === 'object') {
            return {
              data: obj,
              snappyOffset: null,
              v8Offset: v8off,
              version: targetVer,
              compressed: false
            };
          }
        } catch (e) {}
      }
    }
  }

  return null;
}

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath) {
  console.error('Usage: node decompress_blob.js <blob_path> [output_json_path]');
  process.exit(1);
}

try {
  const buf = fs.readFileSync(inputPath);
  console.log(`[INFO] Reading blob: ${inputPath} (${buf.length} bytes)`);

  const result = decodeBlob(buf);
  if (!result) {
    console.error('[ERROR] Could not decompress or deserialize blob format.');
    process.exit(1);
  }

  console.log(`[SUCCESS] Decoded blob! (Snappy offset: ${result.snappyOffset}, V8 offset: ${result.v8Offset}, V8 version: 0x${result.version.toString(16)})`);

  const obj = result.data;
  console.log('--- Metadata ---');
  if (obj.conversationUuid) console.log(`  conversationUuid: ${obj.conversationUuid}`);
  if (obj.product)          console.log(`  product:          ${obj.product}`);
  if (obj.name)             console.log(`  name:             ${obj.name}`);
  if (obj.messageCount)     console.log(`  messageCount:     ${obj.messageCount}`);
  if (obj.tree) {
    console.log(`  tree.kind:        ${obj.tree.kind}`);
    console.log(`  tree.floorSeq:    ${obj.tree.floorSeq}`);
    console.log(`  tree.headSeq:     ${obj.tree.headSeq}`);
    console.log(`  tree.events:      ${obj.tree.events ? obj.tree.events.length : 0}`);
  }

  const jsonStr = JSON.stringify(obj, null, 2);

  if (outputPath) {
    fs.writeFileSync(outputPath, jsonStr, 'utf8');
    console.log(`[INFO] Saved decoded JSON to: ${outputPath} (${jsonStr.length} bytes)`);
  } else {
    console.log(jsonStr);
  }

} catch (err) {
  console.error('[FATAL]', err.message);
  process.exit(1);
}
