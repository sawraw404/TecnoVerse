"use client";

import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationNodeDatum } from "d3-force";
import { ArrowUpRight, Building2, Crosshair, Minus, Plus, Search, X } from "lucide-react";
import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Badge, Card } from "@/components/ui";
import { cx, day } from "@/lib/format";
import type { EdgeKind, Graph, GraphEdge, GraphFact, GraphNode } from "@/lib/types";

type P = GraphNode & SimulationNodeDatum & { x: number; y: number };

const EDGE: Record<EdgeKind, { label: string; hint: string; stroke: string; width: number; dash?: string }> = {
  collaboration: { label: "Stated collaboration", hint: "Named on a company's own public page", stroke: "var(--text)", width: 2.4 },
  suggestion: { label: "Suggested connection", hint: "Judged from public items; a suggestion only", stroke: "var(--blue)", width: 2, dash: "6 5" },
  member: { label: "Park membership", hint: "Member of Blue Science Park", stroke: "var(--primary)", width: 1, dash: "2 4" },
  area: { label: "Focus area", hint: "The company's industry group", stroke: "var(--border-strong)", width: 1 },
};
const ORDER: EdgeKind[] = ["collaboration", "suggestion", "member", "area"];
// colours: --area-* tokens in globals.css
const color = (area: string | null) => `var(--area-${area ?? "other"})`;
const radius = (n: GraphNode) => (n.kind === "park" ? 30 : n.kind === "area" ? 20 : 11);
const W = 1000;
const H = 760;

/** Static layout, computed once and deterministic, so nothing moves unless the user drags it.
 *  Blue Science Park sits in the middle; each focus area is a hub on a ring, with a wider sector for
 *  bigger areas; companies gather around their hub, park members nearer the centre than external ones. */
function layout(graph: Graph): P[] {
  const nodes: P[] = graph.nodes.map((n) => ({ ...n, x: 0, y: 0 }));
  const count = (a: string | null) => nodes.filter((n) => n.kind === "company" && n.area === a).length;
  const hubs = nodes.filter((n) => n.kind === "area");
  const total = hubs.reduce((t, h) => t + count(h.area) + 3, 0);
  const angle = new Map<string, number>();
  let acc = -Math.PI / 2;
  for (const h of hubs) {
    const share = ((count(h.area) + 3) / total) * Math.PI * 2;
    const a = acc + share / 2;
    acc += share;
    angle.set(h.area!, a);
    Object.assign(h, { x: Math.cos(a) * 230, y: Math.sin(a) * 230, fx: Math.cos(a) * 230, fy: Math.sin(a) * 230 });
  }
  for (const [i, n] of nodes.entries()) {
    if (n.kind === "park") Object.assign(n, { fx: 0, fy: 0 });
    if (n.kind === "company") {
      const a = (angle.get(n.area ?? "other") ?? 0) + ((i % 5) - 2) * 0.08;
      const r = n.member ? 300 : 400;
      Object.assign(n, { x: Math.cos(a) * r, y: Math.sin(a) * r });
    }
  }
  const target = (n: P, axis: "x" | "y") => {
    const a = angle.get(n.area ?? "other") ?? 0;
    const r = n.member ? 320 : 420;
    return axis === "x" ? Math.cos(a) * r : Math.sin(a) * r;
  };
  const links = graph.edges.filter((e) => e.kind === "collaboration" || e.kind === "suggestion").map((e) => ({ ...e }));
  forceSimulation(nodes)
    .force("link", forceLink<P, (typeof links)[number]>(links).id((d) => d.id).distance(160).strength(0.04))
    .force("charge", forceManyBody<P>().strength((d) => (d.kind === "company" ? -120 : -400)))
    .force("collide", forceCollide<P>().radius((d) => radius(d) + (d.kind === "company" ? 18 : 30)))
    .force("x", forceX<P>((d) => (d.kind === "company" ? target(d, "x") : 0)).strength((d) => (d.kind === "company" ? 0.18 : 0)))
    .force("y", forceY<P>((d) => (d.kind === "company" ? target(d, "y") : 0)).strength((d) => (d.kind === "company" ? 0.18 : 0)))
    .stop()
    .tick(500);
  // fit the drawing into the canvas, then whole pixels: server and browser floating point differ in the
  // last digits, which would break hydration
  const fit = Math.min(1, (W / 2 - 70) / Math.max(...nodes.map((n) => Math.abs(n.x))), (H / 2 - 50) / Math.max(...nodes.map((n) => Math.abs(n.y))));
  return nodes.map((n) => ({ ...n, x: Math.round(n.x * fit), y: Math.round(n.y * fit) }));
}

function FactLine({ f }: { f: GraphFact }) {
  return (
    <li className="text-[13px] leading-5">
      <span className="text-text">{f.value}</span>
      <span className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-text-3">
        {f.url ? (
          <a href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center font-medium text-primary-text hover:underline">
            source <ArrowUpRight className="size-3" aria-hidden />
          </a>
        ) : (
          <span>no source page</span>
        )}
        {f.retrieved_at && <span>retrieved {day(f.retrieved_at)}</span>}
      </span>
    </li>
  );
}

export function KnowledgeGraph({ graph }: { graph: Graph }) {
  const initial = useMemo(() => layout(graph), [graph]);
  const [pos, setPos] = useState(() => new Map(initial.map((n) => [n.id, { x: n.x, y: n.y }])));
  const byId = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph]);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [hover, setHover] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ node?: string; edge?: number } | null>(null);
  const [shown, setShown] = useState<Record<EdgeKind, boolean>>({ collaboration: true, suggestion: true, member: true, area: true });
  const [areaFilter, setAreaFilter] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id?: string; px: number; py: number; moved: boolean } | null>(null);

  const edges = graph.edges.map((e, i) => ({ ...e, i })).filter((e) => shown[e.kind]);
  const focus = hover ?? selected?.node ?? null;
  const neighbours = useMemo(() => {
    if (!focus) return null;
    const s = new Set([focus]);
    edges.forEach((e) => {
      if (e.source === focus) s.add(e.target);
      if (e.target === focus) s.add(e.source);
    });
    return s;
  }, [focus, edges]);
  const q = query.trim().toLowerCase();
  const matches = (n: GraphNode) => (!q || n.label.toLowerCase().includes(q)) && (!areaFilter || n.kind !== "company" || n.area === areaFilter);
  const dimmed = (id: string) => {
    const n = byId.get(id)!;
    if (neighbours) return !neighbours.has(id);
    return n.kind === "company" && !matches(n);
  };

  // pointer: drag a node, or pan the canvas
  const toWorld = (cx: number, cy: number) => {
    const r = svg.current!.getBoundingClientRect();
    const sx = ((cx - r.left) / r.width) * W - W / 2;
    const sy = ((cy - r.top) / r.height) * H - H / 2;
    return { x: (sx - view.x) / view.k, y: (sy - view.y) / view.k };
  };
  const onDown = (e: ReactPointerEvent, id?: string) => {
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    drag.current = { id, px: e.clientX, py: e.clientY, moved: false };
  };
  const onMove = (e: ReactPointerEvent) => {
    const d = drag.current;
    if (!d) return;
    if (Math.abs(e.clientX - d.px) + Math.abs(e.clientY - d.py) > 3) d.moved = true;
    if (d.id) {
      const w = toWorld(e.clientX, e.clientY);
      setPos((m) => new Map(m).set(d.id!, w));
    } else {
      const r = svg.current!.getBoundingClientRect();
      const dx = ((e.clientX - d.px) / r.width) * W;
      const dy = ((e.clientY - d.py) / r.height) * H;
      d.px = e.clientX;
      d.py = e.clientY;
      setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
    }
  };
  const onUp = () => {
    const d = drag.current;
    drag.current = null;
    if (d && !d.moved) setSelected(d.id ? { node: d.id } : null);
  };
  const zoom = (f: number) => setView((v) => ({ ...v, k: Math.min(3, Math.max(0.4, v.k * f)) }));

  const sel = selected?.node ? byId.get(selected.node) : undefined;
  const selEdge = selected?.edge !== undefined ? graph.edges[selected.edge] : undefined;
  const linksOf = (id: string) => graph.edges.map((e, i) => ({ ...e, i })).filter((e) => (e.kind === "collaboration" || e.kind === "suggestion") && (e.source === id || e.target === id));
  const companies = graph.nodes.filter((n) => n.kind === "company");

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <Card className="overflow-hidden">
        {/* toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2.5 sm:px-4">
          <div className="relative min-w-0 flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-text-3" aria-hidden />
            <label htmlFor="graph-search" className="sr-only">
              Find a company
            </label>
            <input
              id="graph-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Find a company"
              className="h-9 w-full rounded-md border border-border-strong bg-surface pl-8 pr-3 text-sm placeholder:text-text-3 focus:border-ring focus:outline-none focus:ring-3 focus:ring-ring/20"
            />
          </div>
          <div className="ml-auto flex items-center gap-1" role="group" aria-label="Zoom">
            {[
              { label: "Zoom out", icon: Minus, run: () => zoom(1 / 1.25) },
              { label: "Zoom in", icon: Plus, run: () => zoom(1.25) },
              { label: "Reset view", icon: Crosshair, run: () => setView({ x: 0, y: 0, k: 1 }) },
            ].map(({ label, icon: Icon, run }) => (
              <button
                key={label}
                type="button"
                onClick={run}
                aria-label={label}
                title={label}
                className="grid size-9 place-items-center rounded-md border border-border bg-surface text-text-2 transition-colors hover:bg-surface-2 hover:text-text"
              >
                <Icon className="size-4" />
              </button>
            ))}
          </div>
        </div>

        <svg
          ref={svg}
          viewBox={`${-W / 2} ${-H / 2} ${W} ${H}`}
          className="block aspect-[4/3] w-full cursor-grab touch-none select-none bg-[radial-gradient(circle_at_center,var(--surface-2),var(--surface)_70%)] active:cursor-grabbing"
          onPointerDown={(e) => onDown(e)}
          onPointerMove={onMove}
          onPointerUp={onUp}
          onPointerLeave={() => (drag.current = null)}
          onWheel={(e) => zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1)}
          role="img"
          aria-label={`Knowledge graph of ${companies.length} companies. The list below the graph has the same information.`}
        >
          <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
            {edges.map((e) => {
              const a = pos.get(e.source)!;
              const b = pos.get(e.target)!;
              const st = EDGE[e.kind];
              const off = dimmed(e.source) || dimmed(e.target);
              const active = selected?.edge === e.i;
              const clickable = e.kind === "collaboration" || e.kind === "suggestion";
              return (
                <g key={e.i} className={cx("transition-opacity duration-200", off ? "opacity-[0.07]" : "opacity-100")}>
                  {clickable && (
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="transparent"
                      strokeWidth={12}
                      className="cursor-pointer"
                      onPointerDown={(ev) => ev.stopPropagation()}
                      onClick={() => setSelected({ edge: e.i })}
                    >
                      <title>{st.label}</title>
                    </line>
                  )}
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={e.kind === "area" ? color(byId.get(e.target)?.area ?? null) : st.stroke}
                    strokeOpacity={e.kind === "area" ? 0.35 : e.kind === "member" ? 0.45 : 0.85}
                    strokeWidth={active ? st.width + 2 : st.width}
                    strokeDasharray={st.dash}
                    pointerEvents="none"
                  />
                </g>
              );
            })}

            {graph.nodes.map((n) => {
              const p = pos.get(n.id)!;
              const r = radius(n);
              const off = dimmed(n.id);
              const isSel = selected?.node === n.id;
              const showLabel = n.kind !== "company" || n.id === focus || isSel || (q && matches(n)) || view.k > 1.4;
              return (
                <g
                  key={n.id}
                  transform={`translate(${p.x} ${p.y})`}
                  className={cx("cursor-pointer outline-none transition-opacity duration-200", off ? "opacity-20" : "opacity-100")}
                  onPointerDown={(e) => onDown(e, n.id)}
                  onPointerEnter={() => setHover(n.id)}
                  onPointerLeave={() => setHover(null)}
                  tabIndex={0}
                  role="button"
                  aria-label={`${n.label}${n.kind === "company" ? `, ${n.member ? "park member" : "external"}, ${graph.areas[n.area ?? "other"]}` : ""}`}
                  onFocus={() => setHover(n.id)}
                  onBlur={() => setHover(null)}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSelected({ node: n.id })}
                >
                  {n.kind === "park" ? (
                    <>
                      <circle r={r + 8} fill="var(--primary)" opacity={0.12} />
                      <circle r={r} fill="var(--primary)" stroke="var(--surface)" strokeWidth={3} />
                    </>
                  ) : n.kind === "area" ? (
                    <circle r={r} fill="var(--surface)" stroke={color(n.area)} strokeWidth={3.5} />
                  ) : (
                    <circle
                      r={r}
                      fill={n.member ? color(n.area) : "var(--surface)"}
                      stroke={color(n.area)}
                      strokeWidth={n.member ? 2 : 2.6}
                      strokeDasharray={n.member ? undefined : "3 2"}
                    />
                  )}
                  {(isSel || n.id === hover) && <circle r={r + 5} fill="none" stroke="var(--ring)" strokeWidth={2} />}
                  {showLabel && (
                    <text
                      y={r + 14}
                      textAnchor="middle"
                      className={cx("pointer-events-none fill-[var(--text)]", n.kind === "company" ? "text-[11px]" : "text-[12.5px] font-semibold")}
                      style={{ paintOrder: "stroke", stroke: "var(--surface)", strokeWidth: 4, strokeLinejoin: "round" }}
                    >
                      {n.label}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>

        {/* legend */}
        <div className="grid gap-4 border-t border-border px-3 py-3 text-[13px] sm:grid-cols-2 sm:px-4">
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-3">Focus areas</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(graph.areas).map(([key, label]) => {
                const on = areaFilter === key;
                return (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setAreaFilter(on ? null : key)}
                    className={cx(
                      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors",
                      on ? "border-text bg-surface-2" : "border-border hover:bg-surface-2",
                    )}
                  >
                    <span className="size-2.5 rounded-full" style={{ background: color(key) }} aria-hidden />
                    {label}
                    <span className="text-text-3">{companies.filter((c) => c.area === key).length}</span>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-3">
              <span className="inline-flex items-center gap-1.5">
                <span className="size-3 rounded-full bg-text-3" aria-hidden /> park member
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-3 rounded-full border-2 border-dashed border-text-3" aria-hidden /> external
              </span>
            </p>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-3">Links</p>
            <div className="grid gap-1">
              {ORDER.map((k) => (
                <label key={k} className="flex cursor-pointer items-center gap-2" title={EDGE[k].hint}>
                  <input
                    type="checkbox"
                    checked={shown[k]}
                    onChange={() => setShown((s) => ({ ...s, [k]: !s[k] }))}
                    className="size-4 accent-[var(--primary)]"
                  />
                  <svg width="28" height="8" aria-hidden>
                    <line x1="0" y1="4" x2="28" y2="4" stroke={EDGE[k].stroke} strokeWidth={EDGE[k].width} strokeDasharray={EDGE[k].dash} />
                  </svg>
                  {EDGE[k].label}
                  <span className="text-xs text-text-3">{graph.edges.filter((e) => e.kind === k).length}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* details panel */}
      <Card className="h-fit p-4 xl:sticky xl:top-6">
        {sel ? (
          <NodeDetails node={sel} graph={graph} byId={byId} links={linksOf(sel.id)} onClose={() => setSelected(null)} onEdge={(i) => setSelected({ edge: i })} onNode={(id) => setSelected({ node: id })} />
        ) : selEdge ? (
          <EdgeDetails edge={selEdge} byId={byId} onClose={() => setSelected(null)} onNode={(id) => setSelected({ node: id })} />
        ) : (
          <div className="text-sm leading-6 text-text-2">
            <p className="font-medium text-text">Explore the ecosystem</p>
            <p className="mt-1">
              Hover a company to see its links, click it for public facts with sources. Click a solid or dashed blue line for the
              basis of a link. Drag to move, scroll or use the buttons to zoom.
            </p>
            <p className="mt-3 text-xs text-text-3">
              Filled circles are park members, dashed rings are external companies. Colour shows the focus area.
            </p>
          </div>
        )}
      </Card>

      {/* the same information as a list, for keyboard and screen-reader users and small screens */}
      <details className="rounded-lg border border-border bg-surface shadow-sm xl:col-span-2">
        <summary className="cursor-pointer px-4 py-3.5 text-sm font-medium">Companies by focus area (list view)</summary>
        <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(graph.areas).map(([key, label]) => (
            <div key={key}>
              <p className="mb-1.5 flex items-center gap-2 text-sm font-semibold">
                <span className="size-2.5 rounded-full" style={{ background: color(key) }} aria-hidden /> {label}
              </p>
              <ul className="space-y-1 text-sm">
                {companies
                  .filter((c) => c.area === key)
                  .map((c) => (
                    <li key={c.id}>
                      <button type="button" onClick={() => setSelected({ node: c.id })} className="text-left hover:text-primary-text hover:underline">
                        {c.label}
                      </button>{" "}
                      <span className="text-xs text-text-3">{c.member ? "member" : "external"}</span>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

function PanelHeader({ title, sub, onClose }: { title: React.ReactNode; sub?: React.ReactNode; onClose: () => void }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-semibold leading-6">{title}</h2>
        {sub && <div className="mt-1 flex flex-wrap gap-1.5">{sub}</div>}
      </div>
      <button type="button" aria-label="Close details" onClick={onClose} className="grid size-8 shrink-0 place-items-center rounded-md text-text-3 hover:bg-surface-2">
        <X className="size-4" />
      </button>
    </div>
  );
}

function NodeDetails({
  node,
  graph,
  byId,
  links,
  onClose,
  onEdge,
  onNode,
}: {
  node: GraphNode;
  graph: Graph;
  byId: Map<string, GraphNode>;
  links: (GraphEdge & { i: number })[];
  onClose: () => void;
  onEdge: (i: number) => void;
  onNode: (id: string) => void;
}) {
  if (node.kind !== "company") {
    const members = graph.edges.filter((e) => e.target === node.id).map((e) => byId.get(e.source)!);
    return (
      <div>
        <PanelHeader title={node.label} onClose={onClose} />
        <p className="mb-2 text-sm text-text-2">{node.kind === "park" ? `${members.length} park members in this service` : `${members.length} companies`}</p>
        <ul className="max-h-80 space-y-1 overflow-y-auto text-sm">
          {members.map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => onNode(m.id)} className="flex items-center gap-2 text-left hover:text-primary-text hover:underline">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: color(m.area) }} aria-hidden />
                {m.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return (
    <div>
      <PanelHeader
        title={node.label}
        sub={
          <>
            <Badge tone={node.member ? "primary" : "slate"}>{node.member ? "park member" : "external"}</Badge>
            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-medium" style={{ color: color(node.area), background: "var(--surface-2)" }}>
              <span className="size-2 rounded-full" style={{ background: color(node.area) }} aria-hidden />
              {graph.areas[node.area ?? "other"]}
            </span>
          </>
        }
        onClose={onClose}
      />
      {node.website && (
        <a href={node.website} target="_blank" rel="noreferrer" className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-primary-text hover:underline">
          <Building2 className="size-3.5" aria-hidden /> {node.website.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
        </a>
      )}
      {["industry", "offering", "innovation"].map((f) => {
        const facts = node.facts.filter((x) => x.field === f);
        if (!facts.length) return null;
        return (
          <div key={f} className="mb-3">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-3">{f === "offering" ? "Services" : f === "innovation" ? "New innovation" : "Industry"}</p>
            <ul className="space-y-1.5">
              {facts.map((x) => (
                <FactLine key={x.value} f={x} />
              ))}
            </ul>
          </div>
        );
      })}
      <p className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-text-3">Links ({links.length})</p>
      {links.length === 0 && <p className="text-sm text-text-3">No stated collaborations or suggested connections.</p>}
      <ul className="space-y-1">
        {links.map((e) => {
          const other = byId.get(e.source === node.id ? e.target : e.source)!;
          return (
            <li key={e.i}>
              <button type="button" onClick={() => onEdge(e.i)} className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: color(other.area) }} aria-hidden />
                <span className="min-w-0 flex-1 truncate">{other.label}</span>
                <Badge tone={e.kind === "collaboration" ? "slate" : "blue"}>{e.kind === "collaboration" ? "collaboration" : "suggestion"}</Badge>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function EdgeDetails({ edge, byId, onClose, onNode }: { edge: GraphEdge; byId: Map<string, GraphNode>; onClose: () => void; onNode: (id: string) => void }) {
  const a = byId.get(edge.source)!;
  const b = byId.get(edge.target)!;
  return (
    <div>
      <PanelHeader
        title={
          <span className="flex flex-wrap items-center gap-x-1.5">
            <button type="button" className="hover:underline" onClick={() => onNode(a.id)}>
              {a.label}
            </button>
            <span className="text-text-3">↔</span>
            <button type="button" className="hover:underline" onClick={() => onNode(b.id)}>
              {b.label}
            </button>
          </span>
        }
        sub={<Badge tone={edge.kind === "collaboration" ? "slate" : "blue"}>{edge.kind === "collaboration" ? "stated collaboration" : "suggested connection"}</Badge>}
        onClose={onClose}
      />
      {edge.kind === "suggestion" ? (
        <>
          <p className="mb-2 text-xs font-medium text-blue">{edge.label}</p>
          <p className="text-sm leading-6 text-text-2">
            <span className="font-medium text-text">Why:</span> {edge.why}
          </p>
          <p className="mt-2 text-sm leading-6 text-text-2">
            <span className="font-medium text-text">Uncertain:</span> {edge.uncertain}
          </p>
        </>
      ) : (
        <p className="text-sm leading-6 text-text-2">{edge.label}: one company names the other on its own public page.</p>
      )}
      <p className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-text-3">Basis: public items</p>
      <ul className="space-y-2">
        {edge.evidence.map((f) => (
          <FactLine key={f.value} f={f} />
        ))}
      </ul>
    </div>
  );
}
