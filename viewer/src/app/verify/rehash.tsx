"use client";

import { useState } from "react";

export type ManifestFile = { path: string; bytes: number; sha256: string };

type Result = { got: string; ok: boolean };

const hex = (buf: ArrayBuffer) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

/** Re-hash every saved result file in the browser (Web Crypto SHA-256) and compare with the build-time manifest.
 *  "Tamper" flips one bit of one file before hashing, to show what a changed file looks like. */
export function Rehash({ files }: { files: ManifestFile[] }) {
  const [results, setResults] = useState<Record<string, Result>>({});
  const [running, setRunning] = useState(false);
  const [tamper, setTamper] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const target = files.find((f) => f.path === "analysis/facts.json")?.path ?? files[0]?.path;

  async function run() {
    setRunning(true);
    setError(null);
    setResults({});
    try {
      for (const f of files) {
        const res = await fetch(`/results/${f.path}`, { cache: "no-store" });
        if (!res.ok) throw new Error(`${f.path}: HTTP ${res.status}`);
        const bytes = new Uint8Array(await res.arrayBuffer());
        if (tamper && f.path === target) bytes[Math.floor(bytes.length / 2)] ^= 1;
        const got = hex(await crypto.subtle.digest("SHA-256", bytes));
        setResults((r) => ({ ...r, [f.path]: { got, ok: got === f.sha256 } }));
      }
    } catch (e) {
      setError(String(e));
    }
    setRunning(false);
  }

  const done = Object.keys(results).length;
  const failed = Object.values(results).filter((r) => !r.ok).length;
  return (
    <div className="card mt-3">
      <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
        <button
          onClick={run}
          disabled={running}
          className="rounded-lg bg-accent px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-accent-ink disabled:opacity-60"
        >
          {running ? `Hashing… ${done} of ${files.length}` : `Re-hash all ${files.length} files in my browser`}
        </button>
        <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-2">
          <input
            type="checkbox"
            checked={tamper}
            onChange={(e) => {
              setTamper(e.target.checked);
              setResults({});
            }}
            className="h-4 w-4 accent-[var(--amber-mark)]"
          />
          Tamper: flip one bit in <code className="font-mono text-[12px]">{target}</code> before hashing
        </label>
        {done > 0 && !running && (
          <span
            className={`ml-auto rounded-full px-2.5 py-0.5 text-[12px] font-semibold ring-1 ring-inset ${
              failed ? "bg-amber-soft text-amber ring-amber-mark/30" : "bg-accent-soft text-accent-ink ring-accent/20"
            }`}
          >
            {failed ? `${failed} of ${done} changed` : `all ${done} match`}
          </span>
        )}
      </div>
      {error && <p className="border-b border-line p-4 text-[13px] text-amber">{error}</p>}
      <div className="max-h-[520px] overflow-auto">
        <table className="w-full text-left text-[12.5px]">
          <thead className="sticky top-0 bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">File (runs/)</th>
              <th className="px-4 py-2 font-medium">SHA-256 at build</th>
              <th className="px-4 py-2 font-medium">In your browser</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {files.map((f) => {
              const r = results[f.path];
              return (
                <tr key={f.path} className={r && !r.ok ? "bg-amber-soft" : ""}>
                  <td className="px-4 py-2 font-mono text-ink-2">
                    <a href={`/results/${f.path}`} className="hover:text-accent">{f.path}</a>
                  </td>
                  <td className="px-4 py-2 font-mono text-muted" title={f.sha256}>{f.sha256.slice(0, 16)}…</td>
                  <td className="px-4 py-2 font-mono">
                    {!r ? (
                      <span className="text-grey-mark">—</span>
                    ) : r.ok ? (
                      <span className="text-accent-ink" title={r.got}>{r.got.slice(0, 16)}… match</span>
                    ) : (
                      <span className="font-semibold text-amber" title={r.got}>{r.got.slice(0, 16)}… changed</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
