// Design-system primitives. Server-safe: no hooks, no browser APIs.
import { ArrowUpRight, FlaskConical } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { cx } from "@/lib/format";

/* Buttons ---------------------------------------------------------------------------------------- */

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary text-white shadow-sm hover:bg-primary-hover",
  secondary: "bg-surface text-text border border-border-strong shadow-sm hover:bg-surface-2",
  ghost: "text-text-2 hover:bg-surface-2 hover:text-text",
  danger: "bg-surface text-red border border-border-strong hover:bg-red-soft",
};
const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
};

export function buttonClass(variant: Variant = "secondary", size: Size = "md", extra?: string) {
  return cx(
    "inline-flex items-center justify-center rounded-md font-medium whitespace-nowrap select-none",
    "transition-[background-color,color,box-shadow,transform] duration-150 active:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    extra,
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: Variant; size?: Size }) {
  return <button type="button" className={buttonClass(variant, size, className)} {...props} />;
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

/* Badges ----------------------------------------------------------------------------------------- */

export type Tone = "green" | "amber" | "blue" | "red" | "violet" | "slate" | "primary";

const TONES: Record<Tone, string> = {
  green: "bg-green-soft text-green",
  amber: "bg-amber-soft text-amber",
  blue: "bg-blue-soft text-blue",
  red: "bg-red-soft text-red",
  violet: "bg-violet-soft text-violet",
  slate: "bg-slate-soft text-slate",
  primary: "bg-primary-soft text-primary-text",
};

export function Badge({ tone = "slate", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-medium leading-4 whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const STATUS: Record<string, [string, Tone]> = {
  fact: ["fact", "green"],
  inferred: ["inferred", "amber"],
  user_confirmed: ["confirmed", "blue"],
  missing: ["missing", "slate"],
  user_removed: ["removed", "slate"],
};

export function StatusBadge({ status }: { status: string }) {
  const [label, tone] = STATUS[status] ?? [status, "slate"];
  return <Badge tone={tone}>{label}</Badge>;
}

/** Anything cached, curated, hand-seeded or written offline carries this label (CLAUDE.md). */
export function Simulated({ children = "SIMULATED", title }: { children?: ReactNode; title?: string }) {
  return (
    <span title={title}>
      <Badge tone="violet">
        <FlaskConical className="size-3" aria-hidden />
        {children}
      </Badge>
    </span>
  );
}

/* Surfaces --------------------------------------------------------------------------------------- */

export function Card({ className, children, ...props }: ComponentProps<"div">) {
  return (
    <div className={cx("rounded-lg border border-border bg-surface shadow-sm", className)} {...props}>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: {
  title: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-2 flex flex-wrap items-center gap-2">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-text sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-6 text-text-2">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function SectionTitle({ children, count, action }: { children: ReactNode; count?: number; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold text-text">
        {children}
        {count !== undefined && <span className="rounded-full bg-surface-2 px-2 text-xs font-medium text-text-3">{count}</span>}
      </h2>
      {action}
    </div>
  );
}

export type NoticeTone = "info" | "success" | "warning" | "error" | "simulated";

const NOTICE: Record<NoticeTone, string> = {
  info: "border-blue/25 bg-blue-soft text-text",
  success: "border-green/25 bg-green-soft text-text",
  warning: "border-amber/30 bg-amber-soft text-text",
  error: "border-red/30 bg-red-soft text-text",
  simulated: "border-violet/25 bg-violet-soft text-text",
};

export function Notice({
  tone = "info",
  icon,
  title,
  children,
  className,
}: {
  tone?: NoticeTone;
  icon?: ReactNode;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cx("flex gap-3 rounded-md border px-4 py-3 text-sm", NOTICE[tone], className)}>
      {icon && <span className="mt-0.5 shrink-0 [&_svg]:size-4">{icon}</span>}
      <div className="min-w-0 leading-6">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-text-2">{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-border-strong bg-surface px-6 py-12 text-center">
      <div className="mb-3 grid size-11 place-items-center rounded-full bg-surface-2 text-text-3 [&_svg]:size-5">{icon}</div>
      <p className="font-medium text-text">{title}</p>
      {children && <div className="mt-1 max-w-md text-sm leading-6 text-text-2">{children}</div>}
    </div>
  );
}

/** External source link: always opens the original page, so every claim can be checked. */
export function SourceLink({ href, children = "source", className }: { href: string; children?: ReactNode; className?: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className={cx("inline-flex items-center gap-0.5 font-medium text-primary-text underline-offset-2 hover:underline", className)}
    >
      {children}
      <ArrowUpRight className="size-3.5 shrink-0" aria-hidden />
    </a>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse-soft rounded-md bg-surface-2", className)} />;
}
