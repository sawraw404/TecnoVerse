"use client";

import { usePathname } from "next/navigation";
import { useId } from "react";
import { useFormStatus } from "react-dom";
import { ChevronsUpDown, FlaskConical } from "lucide-react";
import { logIn } from "@/app/actions";
import { Spinner } from "@/components/ui";
import type { User } from "@/lib/types";

function Select({ id, users, current, onSwitch }: { id: string; users: User[]; current: string; onSwitch?: () => void }) {
  const { pending } = useFormStatus();
  const special = users.filter((u) => u.role !== "member");
  const members = users.filter((u) => u.role === "member");
  return (
    <div className="relative">
      <select
        id={id}
        name="user"
        defaultValue={current}
        disabled={pending}
        onChange={(e) => {
          e.currentTarget.form?.requestSubmit();
          onSwitch?.(); // closes the mobile menu
        }}
        className="h-9 w-full cursor-pointer appearance-none rounded-md border border-white/10 bg-nav pl-3 pr-8 text-[13px] font-medium text-white transition-colors hover:border-white/25 focus:border-[var(--ring)] focus:outline-none disabled:opacity-60"
      >
        <optgroup label="Blue Science Park and visitors">
          {special.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </optgroup>
        <optgroup label="Company representatives">
          {members.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name.replace(/ representative$/, "")}
            </option>
          ))}
        </optgroup>
      </select>
      <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-nav-muted">
        {pending ? <Spinner className="size-3" /> : <ChevronsUpDown className="size-3.5" aria-hidden />}
      </span>
    </div>
  );
}

/** SIMULATED "log in as", on every page like the Streamlit sidebar. Stays on the same page when the new user may see it. */
export function UserSwitcher({ users, current, onSwitch }: { users: User[]; current: string; onSwitch?: () => void }) {
  const pathname = usePathname();
  const id = useId(); // the desktop sidebar and the mobile menu each render one
  return (
    <form action={logIn}>
      <label htmlFor={id} className="mt-3 mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-nav-muted">
        <FlaskConical className="size-3 text-[#b59cf2]" aria-hidden />
        Log in as · SIMULATED, no real accounts
      </label>
      <input type="hidden" name="next" value={pathname} />
      <Select id={id} users={users} current={current} onSwitch={onSwitch} />
    </form>
  );
}
