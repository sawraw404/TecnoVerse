"use client";

import { ArrowDown, ArrowUp, CheckCircle2, X, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { Move } from "@/lib/types";

type Toast = { id: number; kind: "success" | "error"; title: string; moves?: Move[] };

const EVENT = "tv-toast";

/** Show a toast from any client component: a saved edit (with the rank moves it caused) or an error. */
export function toast(t: Omit<Toast, "id">) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { ...t, id: Date.now() } }));
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  useEffect(() => {
    const onToast = (e: Event) => {
      const t = (e as CustomEvent<Toast>).detail;
      setToasts((all) => [...all.slice(-2), t]);
      setTimeout(() => setToasts((all) => all.filter((x) => x.id !== t.id)), t.moves?.length ? 9000 : 5000);
    };
    window.addEventListener(EVENT, onToast);
    return () => window.removeEventListener(EVENT, onToast);
  }, []);

  return (
    <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end sm:p-6">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto w-full max-w-sm animate-fade-up rounded-lg border border-border bg-surface p-4 shadow-lg"
        >
          <div className="flex items-start gap-3">
            {t.kind === "success" ? (
              <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-green" aria-hidden />
            ) : (
              <XCircle className="mt-0.5 size-5 shrink-0 text-red" aria-hidden />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{t.title}</p>
              {t.moves && t.moves.length > 0 && (
                <ul className="mt-2 space-y-1.5">
                  {t.moves.map((m) => (
                    <li key={m.title} className="flex items-start gap-2 text-[13px] leading-5 text-text-2">
                      <span className={`inline-flex shrink-0 items-center font-semibold tabular-nums ${m.delta > 0 ? "text-green" : "text-red"}`}>
                        {m.delta > 0 ? <ArrowUp className="size-3.5" aria-hidden /> : <ArrowDown className="size-3.5" aria-hidden />}
                        {Math.abs(m.delta)}
                      </span>
                      <span className="min-w-0">
                        {m.title} <span className="text-text-3">· now #{m.rank}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => setToasts((all) => all.filter((x) => x.id !== t.id))}
              className="grid size-6 shrink-0 place-items-center rounded text-text-3 hover:bg-surface-2"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
