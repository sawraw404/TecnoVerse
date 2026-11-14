"use client";

import { Building2, ChevronRight, Globe, Search, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useFormStatus } from "react-dom";
import { logIn } from "@/app/actions";
import type { User } from "@/lib/types";

function Choice({ user, hint }: { user: User; hint: string }) {
  const { pending, data } = useFormStatus();
  const busy = pending && data?.get("user") === user.id;
  const Icon = user.role === "staff" ? ShieldCheck : user.role === "external" ? Globe : Building2;
  return (
    <button
      name="user"
      value={user.id}
      disabled={pending}
      className="group flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-surface-2 disabled:opacity-60"
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-md border border-border bg-surface text-text-2 group-hover:text-primary">
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-text">{user.name.replace(/ representative$/, "")}</span>
        <span className="block truncate text-xs text-text-3">{busy ? "Signing in…" : hint}</span>
      </span>
      <ChevronRight className="size-4 shrink-0 text-text-3 transition-transform group-hover:translate-x-0.5" aria-hidden />
    </button>
  );
}

export function UserPicker({ users }: { users: User[] }) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const special = users.filter((u) => u.role !== "member");
  const members = users.filter((u) => u.role === "member" && u.name.toLowerCase().includes(q));

  return (
    <form action={logIn} className="mt-6 space-y-5">
      <div className="space-y-1">
        {special.map((u) => (
          <Choice key={u.id} user={u} hint={u.role === "staff" ? "Ecosystem view and suggested connections" : "Browse opportunities, no profile"} />
        ))}
      </div>
      <div>
        <label htmlFor="company-search" className="mb-2 block text-xs font-medium uppercase tracking-wide text-text-3">
          Company representatives
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3" aria-hidden />
          <input
            id="company-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${users.length - special.length} companies`}
            autoComplete="off"
            className="h-10 w-full rounded-md border border-border-strong bg-surface pl-9 pr-3 text-sm shadow-sm placeholder:text-text-3 focus:border-ring focus:outline-none focus:ring-3 focus:ring-ring/20"
          />
        </div>
        <div className="mt-2 max-h-[min(46vh,420px)] space-y-1 overflow-y-auto rounded-lg border border-border bg-surface p-1.5 shadow-sm">
          {members.map((u) => (
            <Choice key={u.id} user={u} hint="Company representative" />
          ))}
          {members.length === 0 && <p className="px-3 py-6 text-center text-sm text-text-3">No company matches “{query}”.</p>}
        </div>
      </div>
    </form>
  );
}
