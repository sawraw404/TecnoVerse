import { cx } from "@/lib/format";

/** Wordmark: an orbit around a node, for a park that connects companies. */
export function Logo({ className, dark = false }: { className?: string; dark?: boolean }) {
  return (
    <span className={cx("inline-flex items-center gap-2.5", className)}>
      <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="9" fill="var(--primary)" />
        <ellipse cx="16" cy="16" rx="10" ry="4.6" fill="none" stroke="white" strokeOpacity="0.55" strokeWidth="1.6" transform="rotate(-28 16 16)" />
        <circle cx="16" cy="16" r="3.4" fill="white" />
        <circle cx="24.4" cy="11.3" r="1.7" fill="white" />
      </svg>
      <span className={cx("text-[15px] font-semibold tracking-tight", dark ? "text-white" : "text-text")}>TecnoVerse</span>
    </span>
  );
}
