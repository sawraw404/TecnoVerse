"use client";

import { ArrowUpRight, Contact, Mail, Phone, UserRound } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Dialog } from "@/components/dialog";
import { CopyText } from "@/components/opportunity-actions";
import { Button, buttonClass, SourceLink } from "@/components/ui";
import { day } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

const WHO = { funding: "the funder", event: "the organiser", testbed: "the test environment", news: "the source" };

/** "Contact" button on an opportunity card: a popup with the organiser's published contact route. */
export function ContactButton({ opportunity: o }: { opportunity: Opportunity }) {
  const [open, setOpen] = useState(false);
  const d = o.contact_details;
  const hasRoute = !!d && (d.emails.length > 0 || !!d.phone || !!d.url);

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)} title={`Contact ${WHO[o.type]}`}>
        <Contact className="size-4" aria-hidden />
        <span>Contact</span>
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Contact ${WHO[o.type]}`}
        description={o.title}
      >
        <div className="space-y-4 text-sm">
          {d && hasRoute ? (
            <dl className="space-y-3">
              {d.name && (
                <Row icon={<UserRound className="size-4" aria-hidden />} label="Name">
                  <p className="font-medium text-text">{d.name}</p>
                  {d.role && <p className="text-text-2">{d.role}</p>}
                </Row>
              )}
              {d.emails.map((email) => (
                <Row key={email} icon={<Mail className="size-4" aria-hidden />} label="Email">
                  <p className="break-all text-text">{email}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <a href={`mailto:${email}?subject=${encodeURIComponent(o.title)}`} className={buttonClass("secondary", "sm")}>
                      <Mail className="size-4" aria-hidden /> Email
                    </a>
                    <CopyText text={email} />
                  </div>
                </Row>
              ))}
              {d.phone && (
                <Row icon={<Phone className="size-4" aria-hidden />} label="Phone">
                  <p className="text-text">{d.phone}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <a href={`tel:${d.phone.replace(/[^\d+]/g, "")}`} className={buttonClass("secondary", "sm")}>
                      <Phone className="size-4" aria-hidden /> Call
                    </a>
                    <CopyText text={d.phone} />
                  </div>
                </Row>
              )}
              {d.url && (
                <Row icon={<ArrowUpRight className="size-4" aria-hidden />} label={o.type === "event" ? "Registration and questions" : "Contact page"}>
                  <SourceLink href={d.url} className="break-all">
                    {o.type === "event" ? "Open the event page" : "Open the contact page"}
                  </SourceLink>
                </Row>
              )}
            </dl>
          ) : (
            <p className="rounded-md bg-surface-2 px-3 py-2.5 text-text-2">
              The source does not publish a contact for this {o.type}. The source page is the next step:{" "}
              <SourceLink href={o.url}>open source</SourceLink>
            </p>
          )}

          <p className="border-t border-border pt-3 text-xs leading-5 text-text-3">
            {d ? (
              <>
                Published at <SourceLink href={d.source_url} className="break-all">{new URL(d.source_url).hostname}</SourceLink> · retrieved {day(d.retrieved_at)}.
              </>
            ) : (
              <>Retrieved {day(o.retrieved_at)}.</>
            )}{" "}
            {o.type === "funding"
              ? "A possible match only: the funder decides eligibility."
              : "Contacting them is your own initiative; Blue Science Park makes no commitment on their behalf."}
          </p>
        </div>
      </Dialog>
    </>
  );
}

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-md bg-surface-2 text-text-3">{icon}</span>
      <div className="min-w-0 flex-1">
        <dt className="text-xs font-semibold uppercase tracking-wide text-text-3">{label}</dt>
        <dd className="mt-0.5">{children}</dd>
      </div>
    </div>
  );
}
