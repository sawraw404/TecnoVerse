import { ArrowDown, ArrowUp, CalendarDays, ChevronRight, CircleHelp, FlaskConical, Landmark, Mail, MapPin, Sparkles, Ticket } from "lucide-react";
import { ContactButton } from "@/components/contact-dialog";
import { CardActions, CopyText } from "@/components/opportunity-actions";
import { Badge, Card, Simulated, SourceLink } from "@/components/ui";
import { DATE_LABEL, day, keyDate } from "@/lib/format";
import type { Card as CardData, Company } from "@/lib/types";

const TYPE_ICON = { funding: Landmark, event: Ticket, testbed: FlaskConical, news: Sparkles };
const TYPE_TONE = { funding: "bg-blue-soft text-blue", event: "bg-amber-soft text-amber", testbed: "bg-green-soft text-green", news: "bg-slate-soft text-slate" };

function introEmail(title: string, company: Company) {
  return `Subject: ${title}

Hello,

We are ${company.name} (${company.website}). We saw "${title}" and believe it may fit our work. Could you tell us more about how to take part and whether our profile could be relevant?

Best regards,
${company.name}`;
}

export function OpportunityCard({ card, company }: { card: CardData; company: Company | null }) {
  const o = card.opportunity;
  const m = card.match;
  const Icon = TYPE_ICON[o.type];
  const moved = m?.prev_rank && m.prev_rank !== m.rank ? m.prev_rank - m.rank : 0;
  const reasons = m?.reasons.slice(0, 2).map((r) => r.text) ?? [];

  return (
    <Card className="animate-fade-up overflow-hidden transition-shadow hover:shadow-md">
      <div className="flex gap-4 p-4 sm:p-5">
        <span className={`hidden size-10 shrink-0 place-items-center rounded-md sm:grid ${TYPE_TONE[o.type]}`}>
          <Icon className="size-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {m && <span className="mr-0.5 font-mono text-xs font-semibold text-text-3">#{m.rank}</span>}
            {o.type === "funding" && <Badge tone="blue">possible match</Badge>}
            {moved !== 0 && (
              <Badge tone={moved > 0 ? "green" : "red"}>
                {moved > 0 ? <ArrowUp className="size-3" aria-hidden /> : <ArrowDown className="size-3" aria-hidden />}
                {Math.abs(moved)} since last change
              </Badge>
            )}
            {o.simulated && <Simulated />}
          </div>
          <h3 className="mt-1.5 text-[15.5px] font-semibold leading-6">
            <a href={o.url} target="_blank" rel="noreferrer" className="hover:text-primary-text hover:underline underline-offset-2">
              {o.title}
            </a>
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-3">
            <span className="inline-flex items-center gap-1 font-medium text-text-2">
              <CalendarDays className="size-3.5" aria-hidden />
              {DATE_LABEL[o.type]}: {day(keyDate(o))}
            </span>
            {o.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" aria-hidden />
                {o.location}
              </span>
            )}
            <span>source: {o.type === "news" ? (o.contact ?? o.source) : o.source}</span>
            <span>retrieved {day(o.retrieved_at)}</span>
            <SourceLink href={o.url}>open</SourceLink>
          </p>

          {o.type === "news" ? (
            <div className="mt-3 grid gap-2 text-sm leading-6 sm:grid-cols-2">
              <div className="rounded-md bg-surface-2 px-3 py-2.5">
                <p className="mb-0.5 flex items-center gap-1.5 text-xs font-semibold text-text">
                  What changed <Badge tone="slate">AI summary</Badge>
                </p>
                <p className="text-text-2">{o.summary}</p>
              </div>
              {card.why ? (
                <div className="rounded-md bg-surface-2 px-3 py-2.5">
                  <p className="mb-0.5 text-xs font-semibold text-text">Why it may matter to {company?.name ?? "you"}</p>
                  <p className="text-text-2">{card.why}</p>
                  {card.uncertain && <p className="mt-1 text-xs text-text-3">Check: {card.uncertain}</p>}
                </div>
              ) : (
                company && (
                  <div className="rounded-md bg-surface-2 px-3 py-2.5 text-text-3">Similar to your profile by text; no note written for it.</div>
                )
              )}
            </div>
          ) : card.why ? (
            <div className="mt-3 grid gap-2 text-sm leading-6 sm:grid-cols-2">
              <div className="rounded-md bg-surface-2 px-3 py-2.5">
                <p className="mb-0.5 flex items-center gap-1.5 text-xs font-semibold text-text">
                  Why it fits
                </p>
                <p className="text-text-2">{card.why}</p>
              </div>
              <div className="rounded-md bg-surface-2 px-3 py-2.5">
                <p className="mb-0.5 flex items-center gap-1.5 text-xs font-semibold text-text">
                  <CircleHelp className="size-3.5 text-amber" aria-hidden /> Uncertain
                </p>
                <p className="text-text-2">{card.uncertain}</p>
              </div>
            </div>
          ) : (
            (reasons.length > 0 || (m?.uncertainties.length ?? 0) > 0) && (
              <div className="mt-3 space-y-1 text-sm leading-6 text-text-2">
                {reasons.length > 0 && (
                  <p>
                    <span className="font-medium text-text">Why it may fit:</span> {reasons.join("; ")}
                  </p>
                )}
                {m && m.uncertainties.length > 0 && (
                  <p>
                    <span className="font-medium text-text">Uncertain:</span> {m.uncertainties.join("; ")}
                  </p>
                )}
              </div>
            )
          )}
          {!m && o.summary && o.type !== "news" && <p className="mt-2 line-clamp-3 text-sm leading-6 text-text-2">{o.summary}</p>}
        </div>
      </div>

      {o.type === "news" ? (
        // trends: no organiser to contact, so only Save, votes and "Ask about this"
        m && (
          <div className="flex justify-end border-t border-border bg-surface-2/50 px-4 py-2 sm:px-5">
            <CardActions opportunityId={o.id} title={o.title} vote={card.vote} saved={card.saved} />
          </div>
        )
      ) : (
      <div className="flex flex-col gap-2 border-t border-border bg-surface-2/50 px-4 py-2 sm:flex-row sm:items-start sm:justify-between sm:px-5">
        {m || o.requirements.length > 0 || o.contact || company ? (
          <details className="min-w-0 flex-1 py-1">
            <summary className="inline-flex cursor-pointer items-center gap-1 text-[13px] font-medium text-text-2 hover:text-text">
              <ChevronRight className="chevron size-4 transition-transform" aria-hidden /> Next step
            </summary>
            <div className="mt-3 space-y-3 pb-2 text-sm leading-6">
              {m?.next_step && <p className="text-text">{m.next_step}</p>}
              {o.requirements.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-3">Requirements, as published by the source (not assessed)</p>
                  <ul className="mt-1.5 space-y-1.5">
                    {o.requirements.map((r) => (
                      <li key={r} className="border-l-2 border-border-strong pl-3 text-text-2">
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {o.contact && (
                <p className="text-text-2">
                  <span className="font-medium text-text">Contact:</span> {o.contact}
                </p>
              )}
              {company && (
                <div>
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-3">
                      <Mail className="size-3.5" aria-hidden /> Draft intro email
                    </p>
                    <CopyText text={introEmail(o.title, company)} />
                  </div>
                  <pre className="whitespace-pre-wrap rounded-md border border-border bg-surface px-3 py-2.5 font-sans text-[13px] leading-6 text-text-2">
                    {introEmail(o.title, company)}
                  </pre>
                </div>
              )}
            </div>
          </details>
        ) : (
          <span className="flex-1" />
        )}
        <div className="flex flex-wrap items-center gap-1">
          <ContactButton opportunity={o} />
          {m && <CardActions opportunityId={o.id} title={o.title} vote={card.vote} saved={card.saved} />}
        </div>
      </div>
      )}
    </Card>
  );
}
