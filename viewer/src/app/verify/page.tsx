import { readFileSync } from "node:fs";
import path from "node:path";

import { getVerify } from "@/lib/data";
import { utc } from "@/lib/format";

import { type ManifestFile, Rehash } from "./rehash";

export const metadata = { title: "Check it · Heirloom" };

function manifest(): { built_at: string; files: ManifestFile[] } {
  // Written by scripts/results.mjs before every build, from the same ../runs files the site is built from.
  return JSON.parse(readFileSync(path.join(process.cwd(), "public", "results", "manifest.json"), "utf-8"));
}

export default function Verify() {
  const verify = getVerify();
  const m = manifest();
  const total = m.files.reduce((s, f) => s + f.bytes, 0);
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Check it in your browser</h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        Every page and every number on this site is built from {m.files.length} saved result files in the
        repo&apos;s <code className="font-mono text-[13px]">runs/</code> folder. Below: what{" "}
        <code className="font-mono text-[13px]">heirloom verify</code> found when it last re-checked them, and a way
        to re-hash the files yourself and see that they are the exact files the site was built from.
      </p>

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">What heirloom verify checked</h2>
      {verify ? (
        <>
          <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
            Last run {utc(verify.at)}
            {verify.with_database ? ", with the dataset (quotes and lines found in the raw rows)" : ", without the dataset"}:{" "}
            <b className={verify.passed ? "text-accent-ink" : "text-amber"}>
              {verify.passed ? "every check passed" : "some checks failed"}
            </b>
            .
          </p>
          <div className="card mt-3 divide-y divide-line">
            {verify.checks.map((c) => (
              <div key={c.name} className="flex items-start gap-3 p-4">
                <span
                  className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${
                    c.passed ? "bg-accent-soft text-accent-ink ring-accent/20" : "bg-amber-soft text-amber ring-amber-mark/30"
                  }`}
                >
                  {c.passed ? "pass" : "fail"}
                </span>
                <p className="flex-1 text-[14px] leading-relaxed text-ink-2">{c.name}</p>
                <span className="shrink-0 font-mono text-[12.5px] text-muted">
                  {c.ok.toLocaleString()} ok · {c.failed} failed
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[13px] leading-relaxed text-muted">
            Run it yourself, no dataset needed:{" "}
            <code className="font-mono text-[12.5px]">cd pipeline &amp;&amp; uv run heirloom verify --no-db</code>. With
            the dataset, <code className="font-mono text-[12.5px]">uv run heirloom verify</code> also finds every quote
            and line again in its raw row.
          </p>
        </>
      ) : (
        <p className="mt-2 text-[14px] text-muted">No verify run saved.</p>
      )}

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">Re-hash the result files</h2>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
        At build time each file was hashed (SHA-256, {(total / 1e6).toFixed(1)} MB in all, built {utc(m.built_at)}).
        The button fetches every file from this site and hashes it again with your browser&apos;s own Web Crypto. Turn
        on <b className="text-ink">Tamper</b> to flip a single bit in one file and watch its hash fail. The hashes are
        of the files as stored in git, so <code className="font-mono text-[12.5px]">sha256sum runs/analysis/facts.json</code>{" "}
        on a fresh clone gives the same value.
      </p>
      <Rehash files={m.files} />
    </div>
  );
}
