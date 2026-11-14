import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Users } from "lucide-react";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { Notice, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import type { Graph, Me } from "@/lib/types";

export const metadata: Metadata = { title: "Knowledge graph" };

export default async function GraphPage() {
  const me = await api<Me>("/me");
  if (me.user.role !== "staff") notFound(); // staff only, checked on the server and again by the API
  const graph = await api<Graph>("/graph");
  const companies = graph.nodes.filter((n) => n.kind === "company");
  const members = companies.filter((n) => n.member).length;
  return (
    <>
      <PageHeader
        title="Knowledge graph"
        description={`${companies.length} companies: ${members} Blue Science Park members and ${companies.length - members} external, grouped by the park's focus areas. Built from public profile items only.`}
      />
      <Notice tone="info" icon={<Users />} className="mb-5">
        Suggested connections are <strong className="font-medium text-text">suggestions</strong>: no company has expressed
        interest. Collaborations are links a company states on its own public pages.
      </Notice>
      <KnowledgeGraph graph={graph} />
    </>
  );
}
