// Before every build: copy the saved result files (../runs) into public/results so the /verify page can let anyone
// re-hash them in the browser, and write the manifest of their SHA-256 hashes. Line endings are stored as in git
// (LF), so the hashes match `sha256sum` on a fresh clone of the repo.

import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

const RUNS = process.env.HEIRLOOM_RUNS ?? path.join(process.cwd(), "..", "runs");
const OUT = path.join(process.cwd(), "public", "results");

rmSync(OUT, { recursive: true, force: true });
const files = [];
for (const dir of ["", "analysis"]) {
  mkdirSync(path.join(OUT, dir), { recursive: true });
  for (const name of readdirSync(path.join(RUNS, dir)).sort()) {
    if (!name.endsWith(".json") && !name.endsWith(".json.gz")) continue;
    // Gzipped row files are binary: copied byte for byte. JSON is text: LF line endings, as stored in git.
    const bytes = name.endsWith(".gz")
      ? readFileSync(path.join(RUNS, dir, name))
      : Buffer.from(readFileSync(path.join(RUNS, dir, name), "utf-8").replace(/\r\n/g, "\n"), "utf-8");
    const rel = dir ? `${dir}/${name}` : name;
    writeFileSync(path.join(OUT, rel), bytes);
    files.push({ path: rel, bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") });
  }
}
writeFileSync(path.join(OUT, "manifest.json"), JSON.stringify({ built_at: new Date().toISOString(), files }, null, 1));
console.log(`results: ${files.length} files hashed into public/results/manifest.json`);
