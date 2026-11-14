// Mirrors tecnoverse/core/schemas.py and the response models in tecnoverse/api.py.

export type Role = "member" | "staff" | "external";
export type OpportunityType = "funding" | "event" | "testbed" | "news";
export type Status = "fact" | "inferred" | "missing" | "user_confirmed" | "user_removed";
export type GuardLabel = "in_scope" | "unclear" | "out_of_scope" | "injection" | "needs_staff";
export type PriorityType = "funding" | "event" | "testbed";

export interface User {
  id: string;
  name: string;
  role: Role;
  company_id: string | null;
}

export interface FoundVia {
  directory: string;
  url: string;
  retrieved: string;
}

export interface Company {
  id: string;
  name: string;
  website: string;
  is_member: boolean;
  region: string | null;
  found_via: FoundVia[];
  last_crawled_at: string | null;
  profile_version: number;
  priority_types: PriorityType[];
  simulated: boolean;
}

export interface Me {
  user: User;
  company: Company | null;
}

export interface ProfileItem {
  id: string;
  field: string;
  value: string;
  status: Status;
  source_page_id: string | null;
  quote: string | null;
  quote_verified: boolean;
  reasoning: string | null;
  confidence: number;
  uncertain: boolean;
  visibility: "public" | "private";
  created_by: "profiler" | "user";
  replaces_item_id: string | null;
  updated_at: string;
  needs_review: boolean;
}

export interface PageRef {
  id: string;
  url: string;
  title: string;
  retrieved_at: string;
}

export interface ProfileView {
  company: Company;
  extracted_by: string;
  field_labels: Record<string, string>;
  items: ProfileItem[];
  removed: ProfileItem[];
  pages: PageRef[];
  counts: Record<"fact" | "inferred" | "missing" | "user_confirmed", number>;
}

export interface Move {
  delta: number;
  title: string;
  rank: number;
}

export interface Opportunity {
  id: string;
  type: OpportunityType;
  title: string;
  url: string;
  source: string;
  retrieved_at: string;
  published_at: string | null;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  format: "online" | "in_person" | "hybrid" | null;
  location: string | null;
  audience: string | null;
  requirements: string[];
  contact: string | null;
  summary: string;
  simulated: boolean;
}

export interface Match {
  opportunity_id: string;
  llm_score: number;
  final_score: number;
  rank: number;
  prev_rank: number | null;
  reasons: { text: string; profile_item_id: string | null }[];
  uncertainties: string[];
  next_step: string;
}

export interface Card {
  opportunity: Opportunity;
  match: Match | null;
  why: string | null;
  uncertain: string | null;
  judged: boolean;
}

export interface Dashboard {
  ranked: boolean;
  company: Company | null;
  top: Card[];
  by_type: Record<PriorityType, Card[]>;
  rest: Record<PriorityType, Card[]>;
}

export interface Source {
  id: string;
  title: string;
  url: string;
  date: string | null;
}

export interface ChatReply {
  label: GuardLabel;
  text: string;
  sources: Source[];
}

export interface Evidence {
  company_id: string;
  company: string;
  field: string;
  value: string;
  url: string | null;
  retrieved_at: string | null;
}

export interface ConnectionView {
  company_a: string;
  company_b: string;
  name_a: string;
  name_b: string;
  members: boolean;
  member_a: boolean;
  member_b: boolean;
  theme: string;
  type: string;
  label: string;
  why: string;
  uncertain: string;
  evidence: Evidence[];
}

export interface StaffView {
  company_count: number;
  themes: { theme: string; companies: string[] }[];
  connections: ConnectionView[];
  other_pairs: { name_a: string; name_b: string; score: number; basis: string }[];
}

export type EdgeKind = "member" | "area" | "collaboration" | "suggestion";

export interface GraphFact {
  field: string;
  value: string;
  url: string | null;
  retrieved_at: string | null;
}

export interface GraphNode {
  id: string;
  kind: "park" | "area" | "company";
  label: string;
  area: string | null;
  member: boolean;
  website: string | null;
  facts: GraphFact[];
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: EdgeKind;
  label: string;
  why: string;
  uncertain: string;
  evidence: GraphFact[];
}

export interface Graph {
  areas: Record<string, string>;
  nodes: GraphNode[];
  edges: GraphEdge[];
}
