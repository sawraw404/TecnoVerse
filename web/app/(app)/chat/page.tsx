import type { Metadata } from "next";
import Link from "next/link";
import { Building2, MessageSquareText, Plus } from "lucide-react";
import { ChatPanel } from "@/components/chat-panel";
import { buttonClass, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { cx, day } from "@/lib/format";
import type { ChatMessage, ChatSession, Me, Source } from "@/lib/types";

export const metadata: Metadata = { title: "Assistant" };

function Conversations({ sessions, active }: { sessions: ChatSession[]; active: string | null }) {
  return (
    <nav aria-label="Conversations" className="space-y-1">
      <Link href="/chat" className={buttonClass("primary", "sm", "mb-2 w-full")}>
        <Plus className="size-4" aria-hidden /> New chat
      </Link>
      {sessions.length === 0 && <p className="px-2 py-3 text-center text-xs text-text-3">No saved conversations yet.</p>}
      {sessions.map((s) => (
        <Link
          key={s.session_id}
          href={`/chat?s=${s.session_id}`}
          aria-current={s.session_id === active ? "page" : undefined}
          className={cx(
            "block rounded-md px-2.5 py-2 transition-colors",
            s.session_id === active ? "bg-primary-soft" : "hover:bg-surface-2",
          )}
        >
          <span className="line-clamp-2 text-[13px] font-medium leading-5 text-text">{s.title}</span>
          <span className="mt-0.5 flex items-center gap-1.5 text-[11px] text-text-3">
            {s.opportunity && <MessageSquareText className="size-3 shrink-0" aria-label="About an opportunity" />}
            {s.company && <Building2 className="size-3 shrink-0" aria-label="About a company" />}
            <span className="truncate">{s.opportunity ? s.opportunity.title : s.company ? s.company.name : `${s.messages} messages`}</span>
            <span className="ml-auto shrink-0">{day(s.updated_at)}</span>
          </span>
        </Link>
      ))}
    </nav>
  );
}

export default async function ChatPage({ searchParams }: PageProps<"/chat">) {
  const { s, about } = await searchParams;
  const sessionId = typeof s === "string" ? s : null;
  const aboutId = typeof about === "string" ? about : null;
  const [me, sessions] = await Promise.all([api<Me>("/me"), api<ChatSession[]>("/chats")]);
  const known = sessionId && sessions.some((x) => x.session_id === sessionId) ? sessionId : null;
  const initial = known ? await api<ChatMessage[]>(`/chats/${known}`) : [];
  const aboutSource: Source | null = known
    ? (sessions.find((x) => x.session_id === known)?.opportunity ?? null)
    : aboutId
      ? await api<Source>(`/opportunities/${encodeURIComponent(aboutId)}`).catch(() => null)
      : null;
  return (
    <>
      <PageHeader
        title="Assistant"
        description="Funding, events, test environments, partners, your profile and recommendations, or the right contact at Blue Science Park."
      />
      <div className="grid gap-4 lg:grid-cols-[250px_minmax(0,1fr)]">
        <aside className="hidden h-fit rounded-xl border border-border bg-surface p-2 shadow-sm lg:block">
          <Conversations sessions={sessions} active={known} />
        </aside>
        <details className="rounded-lg border border-border bg-surface shadow-sm lg:hidden">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium">Conversations ({sessions.length})</summary>
          <div className="border-t border-border p-2">
            <Conversations sessions={sessions} active={known} />
          </div>
        </details>
        {/* keyed by user and conversation: switching either starts from that conversation's stored turns */}
        <ChatPanel
          key={`${me.user.id}:${known ?? "new"}:${aboutSource?.id ?? ""}`}
          who={me.company?.name ?? null}
          sessionId={known}
          initial={initial}
          about={aboutSource}
          subject={known ? (sessions.find((x) => x.session_id === known)?.company ?? null) : null}
        />
      </div>
    </>
  );
}
