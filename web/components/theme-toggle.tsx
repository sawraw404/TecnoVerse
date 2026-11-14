"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

const current = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

/** Light/dark switch for the sidebar. The choice is remembered in this browser. */
export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, current, () => "light" as Theme);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => {
        document.documentElement.dataset.theme = next;
        try {
          localStorage.setItem("tv-theme", next);
        } catch {
          /* private mode: the choice lasts for this page only */
        }
      }}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md bg-white/6 text-xs font-medium text-nav-text transition-colors hover:bg-white/12 hover:text-white"
    >
      {theme === "dark" ? <Sun className="size-3.5" aria-hidden /> : <Moon className="size-3.5" aria-hidden />}
      {theme === "dark" ? "Light mode" : "Dark mode"}
    </button>
  );
}
