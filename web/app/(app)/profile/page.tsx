import type { Metadata } from "next";
import { Building2, CheckCircle2, CircleDashed, FileSearch, Globe, History, Lightbulb, Quote, ShieldAlert } from "lucide-react";
import { AddItem, ItemActions, PrioritiesForm, RebuildButton } from "@/components/profile-edit";
import { Badge, Card, EmptyState, Notice, PageHeader, SectionTitle, SourceLink, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { day } from "@/lib/format";
import type { Me, PageRef, ProfileItem, ProfileView } from "@/lib/types";

export const metadata: Metadata = { title: "Profile" };

// The live re-crawl (Profiler on Gemini) is hidden for now; the code, server action and API endpoint stay.
// Set RECRAWL_ENABLED=1 in web/.env.local to show the button again.
const RECRAWL = process.env.RECRAWL_ENABLED === "1";

const FIELD_HINT: Record<string, string> = {
  innovation: "From the company's news, blog posts and newsletters",
  possible_interest: "Inferred by the system, not confirmed by the company. Never weighted as a priority.",
  contact: "The company's published contact route",
};

function Item({ item, page, fieldLabel }: { item: ProfileItem; page?: PageRef; fieldLabel: string }) {
  return (
    <li className="group flex gap-3 px-4 py-3.5 sm:px-5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={item.status} />
          {item.uncertain && <Badge tone="red">uncertain</Badge>}
          {item.visibility === "private" && <Badge tone="slate">private</Badge>}
          {item.needs_review && <Badge tone="amber">needs review</Badge>}
        </div>
        <p className="mt-1.5 text-[15px] leading-6 text-text break-words">{item.value}</p>
        <p className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-text-3">
          {item.created_by === "user" ? (
            <span>Added by you · {day(item.updated_at)}</span>
          ) : page ? (
            <>
              <SourceLink href={page.url} />
              <span>retrieved {day(page.retrieved_at)}</span>
            </>
          ) : (
            <span>no source page</span>
          )}
        </p>
        {(item.quote || item.reasoning) && (
          <details className="mt-2">
            <summary className="inline-flex cursor-pointer items-center gap-1 rounded text-xs font-medium text-text-2 hover:text-text">
              <Quote className="size-3.5" aria-hidden /> Evidence
            </summary>
            <div className="mt-2 rounded-md border border-border bg-surface-2 px-3 py-2.5 text-[13px] leading-6">
              {item.quote && (
                <>
                  <blockquote className="border-l-2 border-primary/60 pl-3 italic text-text">“{item.quote}”</blockquote>
                  <p className="mt-1.5 text-xs text-text-3">
                    {item.quote_verified ? `Quote found on ${page?.url ?? "the page"}` : "This quote was NOT found on the page."}
                  </p>
                </>
              )}
              {item.reasoning && <p className="mt-1.5 text-text-2">{item.reasoning}</p>}
            </div>
          </details>
        )}
      </div>
      <div className="shrink-0 sm:opacity-60 sm:transition-opacity sm:group-hover:opacity-100 sm:focus-within:opacity-100">
        <ItemActions item={item} fieldLabel={fieldLabel} />
      </div>
    </li>
  );
}

function Stat({ label, value, icon, tone }: { label: string; value: number; icon: React.ReactNode; tone: string }) {
  return (
    <Card className="flex items-center gap-3 px-4 py-3.5">
      <span className={`grid size-9 place-items-center rounded-md ${tone} [&_svg]:size-[18px]`}>{icon}</span>
      <div>
        <p className="text-xl font-semibold tabular-nums leading-6">{value}</p>
        <p className="text-xs text-text-3">{label}</p>
      </div>
    </Card>
  );
}

export default async function ProfilePage() {
  const me = await api<Me>("/me");
  if (me.user.role !== "member" || !me.company) {
    return (
      <>
        <PageHeader title="Profile" />
        <EmptyState icon={<Building2 />} title="Profiles belong to companies">
          Log in as a company representative to see and edit that company&apos;s profile.
        </EmptyState>
      </>
    );
  }
  const profile = await api<ProfileView | null>("/profile");
  const company = me.company;

  if (!profile) {
    return (
      <>
        <PageHeader title={company.name} actions={RECRAWL ? <RebuildButton website={company.website} first /> : undefined} />
        <EmptyState icon={<FileSearch />} title="No profile yet">
          {RECRAWL
            ? "Generate a baseline profile from the company's public website. Every item will carry its source and date."
            : "This company has no profile yet."}
        </EmptyState>
      </>
    );
  }

  const pages = new Map(profile.pages.map((p) => [p.id, p]));
  const fields = Object.entries(profile.field_labels);

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            {company.is_member && <Badge tone="primary">Blue Science Park member</Badge>}
            {company.region && <Badge tone="slate">{company.region}</Badge>}
            <Badge tone="slate">version {profile.company.profile_version}</Badge>
          </>
        }
        title={company.name}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <SourceLink href={company.website}>
              <Globe className="mr-1 size-3.5" aria-hidden />
              {company.website.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
            </SourceLink>
            {company.found_via.length > 0 && (
              <span className="text-text-3">
                Listed in{" "}
                {company.found_via.map((f, i) => (
                  <span key={f.url}>
                    {i > 0 && ", "}
                    <a href={f.url} target="_blank" rel="noreferrer" className="hover:text-text hover:underline">
                      {f.directory}
                    </a>{" "}
                    ({f.retrieved})
                  </span>
                ))}
              </span>
            )}
          </span>
        }
        actions={RECRAWL ? <RebuildButton website={company.website} first={false} /> : undefined}
      />

      <div className="space-y-6">
        {profile.company.simulated && (
          <div className="space-y-2">
            {profile.company.simulated && (
              <Notice tone="warning" icon={<ShieldAlert />} title="The live website could not be reached">
                SIMULATED: this profile was built from cached pages.
              </Notice>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Facts with a verified quote" value={profile.counts.fact} icon={<CheckCircle2 />} tone="bg-green-soft text-green" />
          <Stat label="Inferred" value={profile.counts.inferred} icon={<Lightbulb />} tone="bg-amber-soft text-amber" />
          <Stat label="Confirmed by you" value={profile.counts.user_confirmed} icon={<CheckCircle2 />} tone="bg-blue-soft text-blue" />
          <Stat label="Fields with nothing found" value={profile.counts.missing} icon={<CircleDashed />} tone="bg-slate-soft text-slate" />
        </div>
        <p className="-mt-2 text-xs leading-5 text-text-3">
          Built from {profile.pages.length} public pages
          {profile.company.last_crawled_at && `, retrieved ${day(profile.company.last_crawled_at)}`}. Facts are backed by a quote
          found on the page. Inferred items are the system&apos;s guesses.
        </p>

        <Card className="p-4 sm:p-5">
          <SectionTitle>Your priorities</SectionTitle>
          <p className="-mt-1 mb-3 text-sm text-text-2">Set by you. They raise matching opportunities on the Opportunities page.</p>
          <PrioritiesForm current={profile.company.priority_types} />
        </Card>

        <div className="grid gap-4 xl:grid-cols-2">
          {fields.map(([field, label]) => {
            const items = profile.items.filter((i) => i.field === field && i.status !== "missing");
            return (
              <Card key={field} className="flex flex-col overflow-hidden">
                <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
                  <div className="min-w-0">
                    <h2 className="flex items-center gap-2 text-[15px] font-semibold">
                      {label}
                      {items.length > 0 && <span className="text-xs font-medium text-text-3">{items.length}</span>}
                    </h2>
                    {FIELD_HINT[field] && <p className="mt-0.5 text-xs text-text-3">{FIELD_HINT[field]}</p>}
                  </div>
                  <AddItem field={field} fieldLabel={label} />
                </div>
                {items.length ? (
                  <ul className="divide-y divide-border">
                    {items.map((item) => (
                      <Item key={item.id} item={item} fieldLabel={label} page={item.source_page_id ? pages.get(item.source_page_id) : undefined} />
                    ))}
                  </ul>
                ) : (
                  <div className="flex items-center gap-2 px-4 py-4 text-sm text-text-3 sm:px-5">
                    <StatusBadge status="missing" />
                    Nothing found on the public pages. Not filled in with a guess.
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <details className="group rounded-lg border border-border bg-surface shadow-sm">
            <summary className="flex cursor-pointer items-center gap-2 px-4 py-3.5 text-sm font-medium sm:px-5">
              <History className="size-4 text-text-3" aria-hidden /> Corrected or removed by you
              <span className="text-xs text-text-3">{profile.removed.length}</span>
            </summary>
            <ul className="space-y-1.5 border-t border-border px-4 py-3 text-sm sm:px-5">
              {profile.removed.length === 0 && <li className="text-text-3">No corrections yet.</li>}
              {profile.removed.map((i) => (
                <li key={i.id} className="flex flex-wrap gap-x-2 text-text-2">
                  <span className="line-through decoration-text-3">{i.value}</span>
                  <span className="text-text-3">
                    {profile.field_labels[i.field] ?? i.field} · {day(i.updated_at)}
                  </span>
                </li>
              ))}
            </ul>
          </details>
          <details className="rounded-lg border border-border bg-surface shadow-sm">
            <summary className="flex cursor-pointer items-center gap-2 px-4 py-3.5 text-sm font-medium sm:px-5">
              <FileSearch className="size-4 text-text-3" aria-hidden /> Pages read
              <span className="text-xs text-text-3">{profile.pages.length}</span>
            </summary>
            <ul className="space-y-1.5 border-t border-border px-4 py-3 text-sm sm:px-5">
              {profile.pages.map((p) => (
                <li key={p.id} className="flex flex-wrap items-baseline gap-x-2">
                  <SourceLink href={p.url} className="min-w-0 break-all">
                    {p.title || p.url}
                  </SourceLink>
                  <span className="text-xs text-text-3">retrieved {p.retrieved_at.slice(0, 16).replace("T", " ")} UTC</span>
                </li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </>
  );
}
