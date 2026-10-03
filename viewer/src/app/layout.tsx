import type { Metadata } from "next";
import { Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const hanken = Hanken_Grotesk({ variable: "--font-hanken", subsets: ["latin"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Heirloom",
  description:
    "The life of a false belief inside a group of AI agents: born, written into memory, copied, corrected or still held. " +
    "Built on the AI Digest / AI Village dataset.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${hanken.variable} ${jetbrains.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b border-line bg-surface/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-[17px] font-semibold tracking-tight text-ink">Heirloom</span>
              <span className="hidden text-xs text-muted sm:inline">belief trails in agent memory</span>
            </Link>
            <nav className="flex items-center gap-5 text-sm text-ink-2">
              <Link href="/findings" className="hover:text-accent">Findings</Link>
              <Link href="/#trails" className="hover:text-accent">Trails</Link>
              <Link href="/#monitor" className="hover:text-accent">2026</Link>
              <Link href="/method" className="hover:text-accent">Method</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-6 text-xs leading-relaxed text-muted sm:px-6">
            Data: <span className="text-ink-2">AI Digest / AI Village</span> dataset (aidigestorg/ai-village), used for
            research under its terms: no training, no re-identification. Human names, emails and credentials are masked
            on every page. Every number on this site comes from a saved run.
          </div>
        </footer>
      </body>
    </html>
  );
}
