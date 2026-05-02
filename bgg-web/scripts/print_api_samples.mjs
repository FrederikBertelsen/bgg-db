#!/usr/bin/env node
/**
 * Minimal script to capture example JSON payloads from the Flask API.
 * It writes the *raw JSON bodies* from each endpoint into `api-samples/*.json`.
 *
 * Usage:
 *   node scripts/print_api_samples.mjs
 *   node scripts/print_api_samples.mjs --term "catan" --game-id 13
 *
 * Config:
 *   API_BASE_URL=http://localhost:8443 node scripts/print_api_samples.mjs --term "catan" --game-id 13
 *   API_BASE_URL=https://localhost:8443 node scripts/print_api_samples.mjs --term "catan" --game-id 13
 */

import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const baseUrl = (process.env.API_BASE_URL ?? "http://localhost:8443").replace(/\/+$/, "");
const outDir = resolve("api-samples");

function parseArgs(argv) {
  const out = {
    term: "catan",
    gameId: 13,
    cards: null,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--term" || arg === "-t") {
      out.term = argv[i + 1] ?? out.term;
      i++;
      continue;
    }
    if (arg === "--game-id" || arg === "-g") {
      const raw = argv[i + 1];
      if (typeof raw === "string" && raw.includes(",")) {
        // Common slip: passing "13,42" to --game-id.
        // Treat it as --cards and use the first id for /games and /recommend.
        out.cards = raw;
        const first = raw.split(",")[0]?.trim();
        const parsedFirst = first ? Number(first) : NaN;
        if (Number.isFinite(parsedFirst)) out.gameId = parsedFirst;
      } else {
        const parsed = raw ? Number(raw) : NaN;
        if (Number.isFinite(parsed)) out.gameId = parsed;
      }
      i++;
      continue;
    }
    if (arg === "--cards") {
      out.cards = argv[i + 1] ?? null;
      i++;
      continue;
    }
  }

  return out;
}

const args = parseArgs(process.argv.slice(2));
const searchTerm = args.term;
const gameId = args.gameId;

function toQuery(params) {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    usp.set(key, String(value));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

async function fetchJson(path) {
  const url = `${baseUrl}${path}`;
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    // If the backend ever returns non-JSON, preserve it in a JSON wrapper.
    json = { _nonJsonBody: text };
  }

  return { url, status: res.status, ok: res.ok, json };
}

async function saveSample(filename, jsonBody) {
  await mkdir(outDir, { recursive: true });
  const fullPath = resolve(outDir, filename);
  await writeFile(fullPath, JSON.stringify(jsonBody, null, 2) + "\n", "utf8");
  return fullPath;
}

function printSection(title) {
  process.stdout.write(`\n=== ${title} ===\n`);
}

async function main() {
  printSection("Config");
  console.log({ baseUrl, searchTerm, gameId });

  const encodedTerm = encodeURIComponent(searchTerm);

  printSection("/autocomplete/<term>");
  const autocomplete = await fetchJson(`/autocomplete/${encodedTerm}${toQuery({ n: 5 })}`);
  console.log({ status: autocomplete.status, ok: autocomplete.ok, url: autocomplete.url });
  await saveSample("autocomplete.json", autocomplete.json);

  printSection("/search/<term>");
  const search = await fetchJson(`/search/${encodedTerm}${toQuery({ n: 10 })}`);
  console.log({ status: search.status, ok: search.ok, url: search.url });
  await saveSample("search.json", search.json);

  printSection("/games/<id>");
  const game = await fetchJson(`/games/${gameId}`);
  console.log({ status: game.status, ok: game.ok, url: game.url });
  await saveSample("game.json", game.json);

  printSection("/recommend/<id>");
  const recommend = await fetchJson(`/recommend/${gameId}${toQuery({ n: 5 })}`);
  console.log({ status: recommend.status, ok: recommend.ok, url: recommend.url });
  await saveSample("recommend.json", recommend.json);

  if (args.cards) {
    printSection("/cards/<ids_str>");
    const cardsEndpoint = await fetchJson(`/cards/${args.cards}`);
    console.log({ status: cardsEndpoint.status, ok: cardsEndpoint.ok, url: cardsEndpoint.url });
    await saveSample("cards.json", cardsEndpoint.json);
  } else {
    printSection("Skipping /cards/<ids_str>");
    console.log(
      "Provide --cards '13,42' if you want to capture /cards output (requires at least two ids).",
    );
  }

  printSection("Done");
  console.log(`Wrote samples to: ${outDir}`);
  console.log(
    "If requests fail, confirm your base URL (http vs https) and that the backend is running on localhost:8443.",
  );
}

main().catch((err) => {
  console.error("\nScript failed:");
  console.error(err);
  console.error(
    "\nIf you're using https with a self-signed cert locally, Node may reject the connection. Prefer fixing the cert or using http for local dev.",
  );
  process.exitCode = 1;
});
