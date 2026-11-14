import type { Metadata } from "next";
import { FlaskConical } from "lucide-react";
import { Logo } from "@/components/logo";
import { UserPicker } from "@/components/user-picker";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export const metadata: Metadata = { title: "Log in" };

export default async function LoginPage() {
  const users = await api<User[]>("/users");
  return (
    <main className="relative grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section className="relative hidden overflow-hidden bg-nav p-12 text-nav-text lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(60% 50% at 20% 10%, rgb(43 179 190 / 0.28), transparent 70%), radial-gradient(50% 45% at 90% 90%, rgb(36 87 184 / 0.25), transparent 70%)",
          }}
        />
        <Logo dark className="relative" />
        <div className="relative max-w-md">
          <h1 className="text-[34px] font-semibold leading-tight tracking-tight text-white">
            The science park, working for every company in it.
          </h1>
          <p className="mt-4 text-[15px] leading-7 text-nav-text">
            Profiles built from public sources, funding calls, events and test environments matched to each company, and a
            guarded assistant. Every claim carries its source and date.
          </p>
        </div>
        <p className="relative text-xs text-nav-muted">Blue Science Park · Virtual Science Park challenge · BUILD Hackathon 2026</p>
      </section>

      <section className="flex flex-col items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <Logo className="mb-8 lg:hidden" />
          <h2 className="text-2xl font-semibold tracking-tight">Choose who you are</h2>
          <p className="mt-1.5 text-sm leading-6 text-text-2">
            A company representative sees their own profile, matches and chat. Park staff also see the ecosystem view.
          </p>
          <div className="mt-4 flex items-start gap-2 rounded-md border border-violet/25 bg-violet-soft px-3 py-2.5 text-[13px] leading-5 text-text-2">
            <FlaskConical className="mt-0.5 size-4 shrink-0 text-violet" aria-hidden />
            <span>
              <strong className="font-semibold text-violet">SIMULATED login.</strong> No real accounts or passwords: pick a
              user to see the service as them.
            </span>
          </div>
          <UserPicker users={users} />
        </div>
      </section>
    </main>
  );
}
