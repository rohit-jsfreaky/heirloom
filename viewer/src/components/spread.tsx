import { ArrowSquareOut } from "@phosphor-icons/react/ssr";

import { StatusChip } from "@/components/chips";
import { span, utc } from "@/lib/format";
import type { Believer, Trail, TrailNode } from "@/lib/types";

type Node = { name: string; believer: Believer | null; children: Node[] };

const HUMAN = "a human";

/** Who passed it to whom: each copy hangs under the agent whose chat message it most likely came from (the latest
 *  message affirming the belief, from someone else, before the copy was written). */
function tree(trail: Trail): Node[] {
  const held = trail.believers
    .filter((b) => b.status !== "never held" && b.first_held)
    .sort((a, b) => a.first_held!.at.localeCompare(b.first_held!.at));
  const nodes = new Map<string, Node>(held.map((b) => [b.agent, { name: b.agent, believer: b, children: [] }]));
  const parentOf = (b: Believer) => (b.carrier ? b.carrier.agent ?? HUMAN : null);
  for (const b of held) {
    const p = parentOf(b);
    if (p && !nodes.has(p)) nodes.set(p, { name: p, believer: null, children: [] });
  }
  const roots: Node[] = [];
  const attached = new Set<string>();
  // Attach in time order; a parent that would close a loop leaves the copy at the top level instead.
  const ancestors = (name: string, seen = new Set<string>()): Set<string> => {
    const b = nodes.get(name)?.believer;
    const p = b ? parentOf(b) : null;
    if (!p || seen.has(p)) return seen;
    seen.add(p);
    return ancestors(p, seen);
  };
  for (const b of held) {
    const p = parentOf(b);
    if (p && !ancestors(p).has(b.agent) && p !== b.agent) {
      nodes.get(p)!.children.push(nodes.get(b.agent)!);
      attached.add(b.agent);
    }
  }
  for (const n of nodes.values()) if (!attached.has(n.name)) roots.push(n);
  const first = (n: Node): string => n.believer?.first_held?.at ?? n.children.map(first).sort()[0] ?? "";
  return roots.sort((a, b) => first(a).localeCompare(first(b)));
}

export function Spread({ trail }: { trail: Trail }) {
  const roots = tree(trail);
  const held = trail.believers.filter((b) => b.status !== "never held");
  const carried = held.filter((b) => b.carrier).length;
  return (
    <section className="card mt-6 p-5">
      <h2 className="text-sm font-semibold text-ink">How it spread</h2>
      <p className="mt-0.5 max-w-3xl text-xs leading-relaxed text-muted">
        Each copy sits under the agent whose chat message it most likely came from: the latest message from someone
        else that affirms the belief, before the copy was written. {carried} of {held.length} copies have one.
        Agents at the top level have none: they wrote it first, from their own work, or from a message the model did
        not read as affirming it (an announced plan, for example: &ldquo;posting to #846 at 1 PM&rdquo;).
      </p>
      <ul className="mt-4 space-y-1">
        {roots.map((n) => <Branch key={n.name} node={n} depth={0} firstSaid={trail.first_said_in_chat} />)}
      </ul>
    </section>
  );
}

function Branch({ node, depth, firstSaid }: { node: Node; depth: number; firstSaid: TrailNode | null }) {
  const b = node.believer;
  const carrier = b?.carrier;
  return (
    <li className={depth ? "border-l border-line pl-4" : ""}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 py-1 text-[13px]">
        <span className={`font-medium ${b ? "text-ink" : "text-ink-2"}`}>{node.name}</span>
        {b ? (
          <>
            <span className="font-mono text-[11px] text-muted">in memory {utc(b.first_held!.at)}</span>
            {carrier && (
              <a href={carrier.link} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-0.5 text-[11.5px] text-accent hover:underline">
                {span(carrier.at, b.first_held!.at)} after a message <ArrowSquareOut size={11} />
              </a>
            )}
            {b.said_it_first && (
              <span className="text-[11.5px] text-amber">
                said it first{firstSaid?.agent === node.name ? ` in chat, ${utc(firstSaid.at)}` : ""}
              </span>
            )}
            <StatusChip status={b.status} short />
          </>
        ) : (
          <span className="text-[11.5px] text-muted">said it in chat; never wrote it into memory in this scan</span>
        )}
      </div>
      {node.children.length > 0 && (
        <ul className="ml-2 space-y-0.5">
          {node.children.map((c) => <Branch key={c.name} node={c} depth={depth + 1} firstSaid={firstSaid} />)}
        </ul>
      )}
    </li>
  );
}
