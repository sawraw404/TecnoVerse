import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeftRight, ChevronRight, CircleHelp, Layers, Network, Users } from "lucide-react";
import { Badge, Card, EmptyState, Notice, PageHeader, SectionTitle, SourceLink } from "@/components/ui";
import { api } from "@/lib/api";
import { cx, day } from "@/lib/format";
import type { ConnectionView, Me, StaffView } from "@/lib/types";

export const metadata: Metadata = { title: "Ecosystem" };

function Company({ name, member }: { name: string; member: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-semibold">{name}</span>
      {member && <Badge tone="primary">member</Badge>}
    </span>
  );
}

function ConnectionCard({ c }: { c: ConnectionView }) {
  return (
    <Card className="animate-fade-up overflow-hidden">
      <div className="p-4 sm:p-5">
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <Badge tone="slate">{c.theme}</Badge>
          <Badge tone="slate">{c.type}</Badge>
        </div>
        <h3 className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15.5px] leading-7">
          <Company name={c.name_a} member={c.member_a} />
          <ArrowLeftRight className="size-4 text-text-3" aria-label="and" />
          <Company name={c.name_b} member={c.member_b} />
        </h3>
        <p className="mt-1 text-xs font-medium text-blue">{c.label}</p>
        <div className="mt-3 grid gap-2 text-sm leading-6 sm:grid-cols-2">
          <div className="rounded-md bg-surface-2 px-3 py-2.5">
            <p className="mb-0.5 text-xs font-semibold">Why</p>
            <p className="text-text-2">{c.why}</p>
          </div>
          <div className="rounded-md bg-surface-2 px-3 py-2.5">
            <p className="mb-0.5 flex items-center gap-1.5 text-xs font-semibold">
              <CircleHelp className="size-3.5 text-amber" aria-hidden /> Uncertain
            </p>
            <p className="text-text-2">{c.uncertain}</p>
          </div>
        </div>
      </div>
      <div className="border-t border-border bg-surface-2/50 px-4 py-3 sm:px-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-3">Basis: public profile items</p>
        <ul className="grid gap-2 md:grid-cols-2">
          {c.evidence.map((e) => (
            <li key={`${e.company_id}-${e.value}`} className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
              <p className="text-xs text-text-3">
                {e.company} · {e.field}
              </p>
              <p className="mt-0.5 leading-6">“{e.value}”</p>
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-3">
                {e.url ? <SourceLink href={e.url} /> : <span>no source page</span>}
                {e.retrieved_at && <span>retrieved {day(e.retrieved_at)}</span>}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

export default async function StaffPage({ searchParams }: PageProps<"/staff">) {
  const me = await api<Me>("/me");
  if (me.user.role !== "staff") notFound(); // not routable for other roles
  const { all } = await searchParams;
  const showAll = all === "1";
  const v = await api<StaffView>("/staff");
  const shown = showAll ? v.connections : v.connections.filter((c) => c.members);

  return (
    <>
      <PageHeader
        title="Ecosystem"
        description={`Shared themes and suggested connections across ${v.company_count} companies, built from public profile items only.`}
      />
      <Notice tone="info" icon={<Users />} className="mb-6">
        Connections are <strong className="font-medium text-text">suggestions</strong>: no company has expressed interest. Introductions
        are decided by park staff.
      </Notice>

      <section className="mb-8">
        <SectionTitle count={v.themes.length}>
          <Layers className="size-4 text-text-3" aria-hidden /> Shared themes
        </SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {v.themes.map((t) => (
            <Card key={t.theme} className="p-4">
              <div className="flex items-baseline justify-between gap-2">
                <p className="font-semibold">{t.theme}</p>
                <span className="text-xs text-text-3">{t.companies.length} companies</span>
              </div>
              <p className="mt-1.5 text-sm leading-6 text-text-2">{t.companies.join(", ")}</p>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle
          count={shown.length}
          action={
            <div className="flex rounded-md border border-border bg-surface p-0.5 text-[13px] shadow-sm" role="group" aria-label="Filter">
              {[
                { href: "/staff", label: "Park members only", on: !showAll },
                { href: "/staff?all=1", label: "All companies", on: showAll },
              ].map((f) => (
                <Link
                  key={f.href}
                  href={f.href}
                  scroll={false}
                  aria-current={f.on ? "true" : undefined}
                  className={cx("rounded px-2.5 py-1 font-medium transition-colors", f.on ? "bg-primary text-white" : "text-text-2 hover:text-text")}
                >
                  {f.label}
                </Link>
              ))}
            </div>
          }
        >
          <Network className="size-4 text-text-3" aria-hidden /> Suggested connections
        </SectionTitle>
        <div className="space-y-3">
          {shown.map((c) => (
            <ConnectionCard key={`${c.company_a}|${c.company_b}`} c={c} />
          ))}
          {shown.length === 0 && (
            <EmptyState icon={<Network />} title="No suggested connections">
              None of the judged connections is backed by public items right now.
            </EmptyState>
          )}
        </div>
      </section>

      {v.other_pairs.length > 0 && (
        <details className="mt-6 rounded-lg border border-border bg-surface shadow-sm">
          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3.5 text-sm font-medium sm:px-5">
            <ChevronRight className="chevron size-4 text-text-3 transition-transform" aria-hidden />
            Other pairs <span className="text-xs text-text-3">{v.other_pairs.length}</span>
            <span className="ml-auto hidden text-xs font-normal text-text-3 sm:inline">keyword overlap only, not judged relevant</span>
          </summary>
          <ul className="divide-y divide-border border-t border-border">
            {v.other_pairs.map((p) => (
              <li key={`${p.name_a}|${p.name_b}`} className="px-4 py-3 text-sm sm:px-5">
                <p className="flex flex-wrap items-center gap-x-2">
                  <span className="font-medium">{p.name_a}</span>
                  <ArrowLeftRight className="size-3.5 text-text-3" aria-label="and" />
                  <span className="font-medium">{p.name_b}</span>
                  <span className="font-mono text-xs text-text-3">score {p.score.toFixed(2)}</span>
                </p>
                {p.basis && <p className="mt-1 text-xs leading-5 text-text-3">{p.basis}</p>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
