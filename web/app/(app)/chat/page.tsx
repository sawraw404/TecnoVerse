import type { Metadata } from "next";
import { ChatPanel } from "@/components/chat-panel";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

export const metadata: Metadata = { title: "Assistant" };

export default async function ChatPage() {
  const me = await api<Me>("/me");
  return (
    <>
      <PageHeader
        title="Assistant"
        description="Funding, events, test environments, partners, your profile and recommendations, or the right contact at Blue Science Park."
      />
      {/* keyed by user: switching user starts a separate conversation */}
      <ChatPanel key={me.user.id} userId={me.user.id} who={me.company?.name ?? null} />
    </>
  );
}
