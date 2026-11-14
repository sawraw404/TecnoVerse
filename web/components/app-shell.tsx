"use client";

import { Building2, FlaskConical, Info, LayoutDashboard, LogOut, Menu, MessagesSquare, Network, Repeat, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { logOut } from "@/app/actions";
import { Logo } from "@/components/logo";
import { Toaster } from "@/components/toaster";
import { cx } from "@/lib/format";
import type { Me } from "@/lib/types";

const ROLE_LABEL = { member: "Company representative", staff: "Blue Science Park staff", external: "External visitor" };

function nav(me: Me) {
  return [
    { href: "/profile", label: "Profile", icon: Building2, show: me.user.role === "member" },
    { href: "/dashboard", label: "Opportunities", icon: LayoutDashboard, show: true },
    { href: "/chat", label: "Assistant", icon: MessagesSquare, show: true },
    { href: "/staff", label: "Ecosystem", icon: Network, show: me.user.role === "staff" }, // staff only
    { href: "/about", label: "About", icon: Info, show: true },
  ].filter((n) => n.show);
}

function Sidebar({ me, onNavigate }: { me: Me; onNavigate?: () => void }) {
  const pathname = usePathname();
  const who = me.company?.name ?? me.user.name;
  return (
    <div className="flex h-full flex-col bg-nav text-nav-text">
      <div className="flex h-16 items-center px-5">
        <Logo dark />
      </div>
      <nav aria-label="Main" className="flex-1 space-y-0.5 px-3 py-2">
        {nav(me).map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cx(
                "group relative flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors",
                active ? "bg-nav-2 text-white" : "text-nav-text hover:bg-nav-2/60 hover:text-white",
              )}
            >
              <span
                aria-hidden
                className={cx(
                  "absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full bg-primary transition-opacity",
                  active ? "opacity-100" : "opacity-0",
                )}
              />
              <Icon className={cx("size-[18px]", active ? "text-[var(--ring)]" : "text-nav-muted group-hover:text-nav-text")} aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="m-3 rounded-lg border border-white/8 bg-nav-2/70 p-3">
        <div className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-primary/20 text-sm font-semibold text-white">
            {who.slice(0, 1)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">{who}</p>
            <p className="truncate text-xs text-nav-muted">{ROLE_LABEL[me.user.role]}</p>
          </div>
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-[11px] text-nav-muted">
          <FlaskConical className="size-3 text-[#b59cf2]" aria-hidden />
          SIMULATED login, no real accounts
        </p>
        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <Link
            href="/login"
            onClick={onNavigate}
            className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md bg-white/6 text-xs font-medium text-nav-text transition-colors hover:bg-white/12 hover:text-white"
          >
            <Repeat className="size-3.5" aria-hidden /> Switch
          </Link>
          <form action={logOut}>
            <button className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md bg-white/6 text-xs font-medium text-nav-text transition-colors hover:bg-white/12 hover:text-white">
              <LogOut className="size-3.5" aria-hidden /> Log out
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-dvh lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">
        <Sidebar me={me} />
      </aside>

      {/* mobile top bar + drawer */}
      <div className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-surface/85 px-4 backdrop-blur lg:hidden">
        <Logo />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          aria-expanded={open}
          className="grid size-10 place-items-center rounded-md text-text-2 hover:bg-surface-2"
        >
          <Menu className="size-5" />
        </button>
      </div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button aria-label="Close menu" className="absolute inset-0 bg-nav/50 backdrop-blur-[2px]" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] animate-fade-up shadow-lg">
            <Sidebar me={me} onNavigate={() => setOpen(false)} />
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setOpen(false)}
              className="absolute right-3 top-3 grid size-10 place-items-center rounded-md text-nav-text hover:bg-nav-2"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">{children}</main>
      <Toaster />
    </div>
  );
}
