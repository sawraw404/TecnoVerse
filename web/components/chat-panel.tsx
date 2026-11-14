"use client";

import { ArrowUp, Bot, CalendarDays, Link2, MessageSquareText, ShieldAlert, ShieldCheck, ShieldQuestion, UserRound, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition, type ReactNode } from "react";
import { sendChat } from "@/app/actions";
import { Badge, Spinner, type Tone } from "@/components/ui";
import { day } from "@/lib/format";
import type { ChatMessage, GuardLabel, Source } from "@/lib/types";

type Message = { role: "user" | "assistant"; text: string; label?: GuardLabel | null; sources?: Source[]; failed?: boolean };

const LABELS: Record<GuardLabel, [string, Tone, ReactNode]> = {
  in_scope: ["in scope", "green", <ShieldCheck key="i" className="size-3" aria-hidden />],
  unclear: ["clarifying", "amber", <ShieldQuestion key="u" className="size-3" aria-hidden />],
  out_of_scope: ["out of scope", "slate", <ShieldQuestion key="o" className="size-3" aria-hidden />],
  injection: ["blocked: rule change", "red", <ShieldAlert key="j" className="size-3" aria-hidden />],
  needs_staff: ["referred to staff", "blue", <Users key="s" className="size-3" aria-hidden />],
};

const SUGGESTIONS = [
  "Which funding calls fit us?",
  "Where can we test our product?",
  "Which events should we attend?",
  "Who at Blue Science Park should we contact about funding?",
];

/** Turn bare URLs in assistant text into links; everything else stays plain text. */
function linkify(text: string) {
  return text.split(/(https?:\/\/[^\s),]+)/g).map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a key={i} href={part} target="_blank" rel="noreferrer" className="break-all text-primary-text underline underline-offset-2">
        {part}
      </a>
    ) : (
      part
    ),
  );
}

/** One stored conversation. Earlier turns live on the server (per company), so they survive reloads and
 *  logins and never mix between companies. `about` attaches an opportunity ("Ask about this"). */
export function ChatPanel({
  who,
  sessionId,
  initial,
  about,
}: {
  who: string | null;
  sessionId: string | null;
  initial: ChatMessage[];
  about: Source | null;
}) {
  const [messages, setMessages] = useState<Message[]>(initial);
  const [draft, setDraft] = useState("");
  const [pending, start] = useTransition();
  const end = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending]);

  const send = (text: string) => {
    const message = text.trim();
    if (!message || pending) return;
    const next = [...messages, { role: "user" as const, text: message }];
    setMessages(next);
    setDraft("");
    start(async () => {
      const r = await sendChat(message, sessionId, about?.id ?? null);
      const reply: Message = { role: "assistant", text: r.text, label: r.label, sources: r.sources, failed: "error" in r };
      setMessages([...next, reply]);
      // a new conversation gets its own address, so it shows in the list and can be reopened
      if (!sessionId && r.session_id) router.replace(`/chat?s=${r.session_id}`, { scroll: false });
    });
  };

  return (
    <div className="flex h-[calc(100dvh-13rem)] min-h-[420px] flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-sm lg:h-[calc(100dvh-14rem)]">
      {about && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-border bg-surface-2/60 px-4 py-2.5 text-[13px] sm:px-6">
          <MessageSquareText className="size-4 shrink-0 text-primary-text" aria-hidden />
          <span className="text-text-3">About</span>
          <a href={about.url} target="_blank" rel="noreferrer" className="min-w-0 font-medium text-primary-text hover:underline">
            {about.title}
          </a>
          <span className="text-xs text-text-3">{about.date ? day(about.date) : "no date stated"}</span>
        </div>
      )}
      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6" aria-live="polite">
        {messages.length === 0 && about && (
          <div className="mx-auto flex max-w-lg flex-col items-center pt-6 text-center">
            <p className="font-medium">Ask anything about this opportunity</p>
            <p className="mt-1 text-sm leading-6 text-text-2">The assistant answers from the collected data and your company profile.</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {["Does this fit us?", "What are the requirements?", "Who should we contact about it?"].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="rounded-full border border-border-strong bg-surface px-3.5 py-1.5 text-[13px] text-text-2 transition-colors hover:border-primary/50 hover:bg-primary-soft hover:text-primary-text"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.length === 0 && !about && (
          <div className="mx-auto flex max-w-lg flex-col items-center pt-6 text-center">
            <div className="mb-3 grid size-12 place-items-center rounded-full bg-primary-soft text-primary-text">
              <Bot className="size-6" aria-hidden />
            </div>
            <p className="font-medium">Ask about funding, events, test environments, partners or your profile</p>
            <p className="mt-1 text-sm leading-6 text-text-2">
              {who ? `Answers use only ${who}'s own data` : "Answers use"} and the collected opportunities, with a link and date for
              each.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-full border border-border-strong bg-surface px-3.5 py-1.5 text-[13px] text-text-2 transition-colors hover:border-primary/50 hover:bg-primary-soft hover:text-primary-text"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex animate-fade-up gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            <span
              className={`grid size-8 shrink-0 place-items-center rounded-full ${
                m.role === "user" ? "bg-surface-2 text-text-2" : "bg-primary-soft text-primary-text"
              }`}
            >
              {m.role === "user" ? <UserRound className="size-4" aria-hidden /> : <Bot className="size-4" aria-hidden />}
            </span>
            <div className={`min-w-0 max-w-[85%] ${m.role === "user" ? "items-end text-right" : ""} flex flex-col`}>
              {m.label && (
                <div className="mb-1.5">
                  <Badge tone={m.failed ? "red" : LABELS[m.label][1]}>
                    {LABELS[m.label][2]}
                    {m.failed ? "error" : LABELS[m.label][0]}
                  </Badge>
                </div>
              )}
              <div
                className={`whitespace-pre-wrap rounded-xl px-4 py-2.5 text-left text-sm leading-6 ${
                  m.role === "user" ? "rounded-tr-sm bg-primary text-white" : "rounded-tl-sm border border-border bg-surface-2 text-text"
                }`}
              >
                {m.role === "assistant" ? linkify(m.text) : m.text}
              </div>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 w-full rounded-lg border border-border bg-surface px-3 py-2 text-left">
                  <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-text-3">
                    <Link2 className="size-3.5" aria-hidden /> Sources
                  </p>
                  <ul className="space-y-1">
                    {m.sources.map((s) => (
                      <li key={s.id} className="flex flex-wrap items-center gap-x-2 text-[13px]">
                        <a href={s.url} target="_blank" rel="noreferrer" className="font-medium text-primary-text hover:underline">
                          {s.title}
                        </a>
                        <span className="inline-flex items-center gap-1 text-xs text-text-3">
                          <CalendarDays className="size-3" aria-hidden />
                          {s.date ? day(s.date) : "no date stated"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {pending && (
          <div className="flex gap-3">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-soft text-primary-text">
              <Bot className="size-4" aria-hidden />
            </span>
            <div className="flex items-center gap-2 rounded-xl rounded-tl-sm border border-border bg-surface-2 px-4 py-2.5 text-sm text-text-2">
              <Spinner /> Checking the question…
            </div>
          </div>
        )}
        <div ref={end} />
      </div>

      <form
        className="border-t border-border bg-surface p-3 sm:p-4"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <div className="flex items-end gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 shadow-sm focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/20">
          <label htmlFor="chat-input" className="sr-only">
            Ask a question
          </label>
          <textarea
            id="chat-input"
            rows={1}
            value={draft}
            maxLength={2000}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(draft);
              }
            }}
            placeholder="Ask a question"
            className="max-h-40 min-h-6 flex-1 resize-none bg-transparent py-1 text-sm leading-6 placeholder:text-text-3 focus:outline-none [field-sizing:content]"
          />
          <button
            type="submit"
            disabled={pending || !draft.trim()}
            aria-label="Send"
            className="grid size-8 shrink-0 place-items-center rounded-md bg-primary text-white transition-colors hover:bg-primary-hover disabled:opacity-40"
          >
            <ArrowUp className="size-4" />
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-text-3">
          Every message is checked against the service&apos;s remit. Decisions and commitments are referred to Blue Science Park staff.
        </p>
      </form>
    </div>
  );
}
