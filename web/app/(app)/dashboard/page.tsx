import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, Inbox, Info } from "lucide-react";
import { OpportunityCard } from "@/components/opportunity-card";
import { Badge, EmptyState, Notice, PageHeader, SectionTitle, SourceLink } from "@/components/ui";
import { api } from "@/lib/api";
import { DATE_LABEL, TYPE_LABEL, cx, day, keyDate } from "@/lib/format";
import type { Dashboard, PriorityType } from "@/lib/types";

export const metadata: Metadata = { title: "Opportunities" };

const TYPES: PriorityType[] = ["funding", "event", "testbed"];
type Tab = "top" | PriorityType;

export default async function DashboardPage({ searchParams }: PageProps<"/dashboard">) {
  const { tab: raw } = await searchParams;
  const d = await api<Dashboard>("/dashboard");
  const total = TYPES.reduce((n, t) => n + d.by_type[t].length + d.rest[t].length, 0);

  if (total === 0) {
    return (
      <>
        <PageHeader title="Opportunities" />
        <EmptyState icon={<Inbox />} title="No opportunities collected yet">
          Run the monitors from the tecnoverse folder: <code className="font-mono text-xs">python -m agents.monitors --run</code>
        </EmptyState>
      </>
    );
  }

  if (!d.ranked) {
    return (
      <>
        <PageHeader
          title="Opportunities"
          description="Everything the monitors collected, soonest first. Log in as a company to see them ranked for that company."
        />
        <div className="space-y-8">
          {TYPES.map((t) => (
            <section key={t}>
              <SectionTitle count={d.by_type[t].length}>{TYPE_LABEL[t]}</SectionTitle>
              <div className="space-y-3">
                {d.by_type[t].map((c) => (
                  <OpportunityCard key={c.opportunity.id} card={c} company={null} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </>
    );
  }

  const tab: Tab = raw === "funding" || raw === "event" || raw === "testbed" ? raw : "top";
  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "top", label: "Top matches", count: d.top.length },
    ...TYPES.map((t) => ({ id: t as Tab, label: TYPE_LABEL[t], count: d.by_type[t].length })),
  ];
  const cards = tab === "top" ? d.top : d.by_type[tab];
  const rest = tab === "top" ? [] : d.rest[tab];

  return (
    <>
      <PageHeader
        eyebrow={
          d.company!.priority_types.length > 0 && (
            <>
              <span className="text-xs text-text-3">Your priorities:</span>
              {d.company!.priority_types.map((p) => (
                <Badge key={p} tone="primary">
                  {TYPE_LABEL[p]}
                </Badge>
              ))}
            </>
          )
        }
        title="Opportunities"
        description={`Funding, events and test environments ranked for ${d.company!.name}.`}
      />

      <Notice tone="info" icon={<Info />} className="mb-6">
        Funding is always a <strong className="font-medium text-text">possible match</strong>: eligibility is never assessed here and
        is decided by the funder.
      </Notice>

      <nav aria-label="Opportunity types" className="mb-5 flex gap-1 overflow-x-auto rounded-lg border border-border bg-surface p-1 shadow-sm">
        {tabs.map((t) => (
          <Link
            key={t.id}
            href={t.id === "top" ? "/dashboard" : `/dashboard?tab=${t.id}`}
            scroll={false}
            aria-current={tab === t.id ? "page" : undefined}
            className={cx(
              "inline-flex h-9 shrink-0 items-center gap-2 rounded-md px-3.5 text-sm font-medium transition-colors",
              tab === t.id ? "bg-primary text-white shadow-sm" : "text-text-2 hover:bg-surface-2 hover:text-text",
            )}
          >
            {t.label}
            <span className={cx("rounded-full px-1.5 text-xs tabular-nums", tab === t.id ? "bg-white/20" : "bg-surface-2 text-text-3")}>
              {t.count}
            </span>
          </Link>
        ))}
      </nav>

      {tab === "top" && <p className="mb-4 text-sm text-text-2">Best matches across all types. Your priorities on the Profile page move types up here.</p>}

      <div className="space-y-3">
        {cards.map((c) => (
          <OpportunityCard key={c.opportunity.id} card={c} company={d.company} />
        ))}
        {cards.length === 0 && (
          <EmptyState icon={<Inbox />} title={`No ${tab === "top" ? "opportunities" : TYPE_LABEL[tab as PriorityType].toLowerCase()} judged relevant right now`}>
            {rest.length > 0 ? "The ones below only share keywords with your profile." : "Check back after the next monitor run."}
          </EmptyState>
        )}
      </div>

      {rest.length > 0 && (
        <details className="mt-6 rounded-lg border border-border bg-surface shadow-sm">
          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3.5 text-sm font-medium sm:px-5">
            <ChevronRight className="chevron size-4 text-text-3 transition-transform" aria-hidden />
            Other {TYPE_LABEL[tab as PriorityType].toLowerCase()}
            <span className="text-xs text-text-3">{rest.length}</span>
            <span className="ml-auto hidden text-xs font-normal text-text-3 sm:inline">keyword overlap only, not judged relevant</span>
          </summary>
          <ul className="divide-y divide-border border-t border-border">
            {rest.map(({ opportunity: o }) => (
              <li key={o.id} className="flex flex-col gap-1 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-5">
                <SourceLink href={o.url} className="min-w-0">
                  {o.title}
                </SourceLink>
                <span className="shrink-0 text-xs text-text-3">
                  {DATE_LABEL[o.type]} {day(keyDate(o))}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
