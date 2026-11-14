import type { Metadata } from "next";
import { Building2, FlaskConical, Handshake, MessagesSquare, Radar, Scale } from "lucide-react";
import { Badge, Card, PageHeader, Simulated, StatusBadge } from "@/components/ui";

export const metadata: Metadata = { title: "About" };

const AGENTS = [
  { icon: Building2, name: "Profiler", text: "Builds a baseline profile from a company's public website. Every item has a source, a date and a status." },
  { icon: Radar, name: "Monitors", text: "Collect funding calls (Vinnova), events and test environments from public sources." },
  { icon: Scale, name: "Matcher", text: "Ranks opportunities for each company and explains the fit and what is uncertain." },
  { icon: MessagesSquare, name: "Assistant", text: "Answers within the science park's purpose and redirects everything else. A guardrail checks every message." },
  { icon: Handshake, name: "Staff mapper", text: "Suggests connections between companies from public information only." },
];

const LABELS: [React.ReactNode, string][] = [
  [<StatusBadge key="f" status="fact" />, "Stated on a public page, with a quote found again in the page text."],
  [<StatusBadge key="i" status="inferred" />, "The system's guess. Never treated as a confirmed company priority."],
  [<StatusBadge key="m" status="missing" />, "Nothing found. Shown as missing, never filled in with a guess."],
  [<StatusBadge key="c" status="user_confirmed" />, "Set or corrected by the company."],
  [<Badge key="u" tone="red">uncertain</Badge>, "Low confidence or contradicting sources."],
  [<Simulated key="s" />, "Cached, curated, placeholder or offline-written data, not a live result."],
];

export default function AboutPage() {
  return (
    <>
      <PageHeader
        title="About TecnoVerse"
        description="A prototype for the Blue Science Park Virtual Science Park challenge, BUILD Hackathon 2026, Karlskrona."
      />
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section>
          <h2 className="mb-3 text-[15px] font-semibold">Agents</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {AGENTS.map(({ icon: Icon, name, text }) => (
              <Card key={name} className="p-4">
                <span className="mb-3 grid size-9 place-items-center rounded-md bg-primary-soft text-primary-text">
                  <Icon className="size-[18px]" aria-hidden />
                </span>
                <p className="font-semibold">{name}</p>
                <p className="mt-1 text-sm leading-6 text-text-2">{text}</p>
              </Card>
            ))}
          </div>
        </section>
        <section className="space-y-6">
          <div>
            <h2 className="mb-3 text-[15px] font-semibold">What the labels mean</h2>
            <Card className="divide-y divide-border">
              {LABELS.map(([badge, text], i) => (
                <div key={i} className="flex items-start gap-3 px-4 py-3">
                  <span className="w-28 shrink-0">{badge}</span>
                  <p className="text-sm leading-6 text-text-2">{text}</p>
                </div>
              ))}
            </Card>
          </div>
          <Card className="flex gap-3 p-4">
            <FlaskConical className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
            <p className="text-sm leading-6 text-text-2">
              Funding is always a <strong className="font-medium text-text">possible match</strong>, never confirmed eligibility.
              Decisions and commitments are made by Blue Science Park staff, not by this service.
            </p>
          </Card>
        </section>
      </div>
    </>
  );
}
