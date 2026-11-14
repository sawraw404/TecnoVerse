"use client";

import { Check, MoreHorizontal, PencilLine, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import {
  addItem,
  confirmItem,
  correctItem,
  rebuildProfile,
  removeItem,
  setPriorities,
  type EditResult,
} from "@/app/actions";
import { Dialog, inputClass } from "@/components/dialog";
import { toast } from "@/components/toaster";
import { Button, Spinner } from "@/components/ui";
import type { PriorityType, ProfileItem } from "@/lib/types";

function report(r: EditResult, what: string) {
  if (r.ok) {
    toast({ kind: "success", title: r.moves.length ? `${what}. Your ranking changed:` : `${what}. Ranking updated.`, moves: r.moves });
  } else {
    toast({ kind: "error", title: r.error });
  }
  return r.ok;
}

/** Confirm, correct or remove one profile item. Corrections keep the original in the history. */
export function ItemActions({ item, fieldLabel }: { item: ProfileItem; fieldLabel: string }) {
  const [mode, setMode] = useState<"menu" | "correct" | "remove" | null>(null);
  const [value, setValue] = useState(item.value);
  const [pending, start] = useTransition();
  const close = () => setMode(null);

  const run = (fn: () => Promise<EditResult>, what: string) =>
    start(async () => {
      if (report(await fn(), what)) close();
    });

  return (
    <>
      <Button variant="ghost" size="sm" className="size-8 px-0" aria-label={`Edit “${item.value}”`} onClick={() => setMode("menu")}>
        <MoreHorizontal className="size-4" />
      </Button>
      <Dialog
        open={mode !== null}
        onClose={close}
        title={mode === "correct" ? "Correct this item" : mode === "remove" ? "Remove this item?" : "Edit profile item"}
        description={
          <>
            <span className="text-text-3">{fieldLabel}:</span> “{item.value}”
          </>
        }
      >
        {mode === "menu" && (
          <div className="grid gap-2">
            {item.status !== "user_confirmed" && (
              <Button disabled={pending} className="justify-start" onClick={() => run(() => confirmItem(item.id), "Confirmed")}>
                {pending ? <Spinner /> : <Check className="size-4 text-green" aria-hidden />}
                Confirm as correct
                <span className="ml-auto text-xs font-normal text-text-3">keeps source and quote</span>
              </Button>
            )}
            <Button className="justify-start" onClick={() => setMode("correct")}>
              <PencilLine className="size-4 text-blue" aria-hidden /> Correct it
              <span className="ml-auto text-xs font-normal text-text-3">original kept in history</span>
            </Button>
            <Button variant="danger" className="justify-start" onClick={() => setMode("remove")}>
              <Trash2 className="size-4" aria-hidden /> Remove
            </Button>
          </div>
        )}
        {mode === "correct" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (value.trim() && value !== item.value) run(() => correctItem(item.id, value), "Correction saved");
            }}
          >
            <label htmlFor="correct-value" className="mb-1.5 block text-sm font-medium">
              Correct value
            </label>
            <input id="correct-value" className={inputClass} value={value} onChange={(e) => setValue(e.target.value)} autoFocus required />
            <p className="mt-2 text-xs leading-5 text-text-3">
              Saved as confirmed by you and private: it is used for your own matching and chat only.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button onClick={() => setMode("menu")}>Back</Button>
              <Button type="submit" variant="primary" disabled={pending || !value.trim() || value === item.value}>
                {pending && <Spinner />} Save correction
              </Button>
            </div>
          </form>
        )}
        {mode === "remove" && (
          <div>
            <p className="text-sm leading-6 text-text-2">
              It is marked as removed by you, stays in your correction history, and a re-crawl will not add it back.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button onClick={() => setMode("menu")}>Back</Button>
              <Button variant="danger" disabled={pending} onClick={() => run(() => removeItem(item.id), "Removed")}>
                {pending && <Spinner />} Remove
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </>
  );
}

export function AddItem({ field, fieldLabel }: { field: string; fieldLabel: string }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [pending, start] = useTransition();
  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)} aria-label={`Add to ${fieldLabel}`}>
        <Plus className="size-4" aria-hidden /> Add
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={`Add to ${fieldLabel.toLowerCase()}`}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            start(async () => {
              if (report(await addItem(field, value), "Added")) {
                setOpen(false);
                setValue("");
              }
            });
          }}
        >
          <label htmlFor={`add-${field}`} className="mb-1.5 block text-sm font-medium">
            Value
          </label>
          <input id={`add-${field}`} className={inputClass} value={value} onChange={(e) => setValue(e.target.value)} autoFocus required />
          <p className="mt-2 text-xs leading-5 text-text-3">Saved as confirmed by you and private.</p>
          <div className="mt-5 flex justify-end gap-2">
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={pending || !value.trim()}>
              {pending && <Spinner />} Add
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

const PRIORITIES: { type: PriorityType; label: string; hint: string }[] = [
  { type: "funding", label: "Funding is a priority", hint: "Raises funding calls" },
  { type: "event", label: "Events are a priority", hint: "Raises events" },
  { type: "testbed", label: "Testing is a priority", hint: "Raises test environments" },
];

export function PrioritiesForm({ current }: { current: PriorityType[] }) {
  const [chosen, setChosen] = useState<PriorityType[]>(current);
  const [pending, start] = useTransition();
  const changed = [...chosen].sort().join() !== [...current].sort().join();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => void report(await setPriorities(chosen), "Priorities saved"));
      }}
    >
      <fieldset className="grid gap-2 sm:grid-cols-3">
        <legend className="sr-only">Priorities</legend>
        {PRIORITIES.map((p) => {
          const on = chosen.includes(p.type);
          return (
            <label
              key={p.type}
              className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 transition-colors ${
                on ? "border-primary/50 bg-primary-soft" : "border-border hover:bg-surface-2"
              }`}
            >
              <input
                type="checkbox"
                checked={on}
                onChange={() => setChosen((c) => (on ? c.filter((t) => t !== p.type) : [...c, p.type]))}
                className="mt-0.5 size-4 accent-[var(--primary)]"
              />
              <span>
                <span className="block text-sm font-medium">{p.label}</span>
                <span className="block text-xs text-text-3">{p.hint}</span>
              </span>
            </label>
          );
        })}
      </fieldset>
      <div className="mt-3 flex items-center justify-end gap-3">
        {changed && <span className="text-xs text-text-3">Unsaved changes</span>}
        <Button type="submit" variant="primary" size="sm" disabled={!changed || pending}>
          {pending && <Spinner />} Save priorities
        </Button>
      </div>
    </form>
  );
}

export function RebuildButton({ website, first }: { website: string; first: boolean }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  return (
    <>
      <Button variant={first ? "primary" : "secondary"} onClick={() => setOpen(true)}>
        <RefreshCw className="size-4" aria-hidden /> {first ? "Generate baseline profile" : "Re-crawl"}
      </Button>
      <Dialog
        open={open}
        onClose={() => !pending && setOpen(false)}
        title={first ? "Generate a baseline profile" : "Re-crawl and rebuild the profile"}
        description={
          <>
            Reads up to 8 public pages of {website} plus recent news and extracts a profile with the live Profiler (Gemini).
            {!first && " Your confirmed, corrected and removed items and your priorities are kept."}
          </>
        }
      >
        <div className="flex justify-end gap-2">
          <Button disabled={pending} onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={pending}
            onClick={() =>
              start(async () => {
                const r = await rebuildProfile();
                if (r.ok) {
                  toast({ kind: "success", title: "Profile rebuilt from the live website." });
                  setOpen(false);
                } else toast({ kind: "error", title: r.error });
              })
            }
          >
            {pending ? (
              <>
                <Spinner /> Reading pages…
              </>
            ) : (
              "Start"
            )}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
