"use client";

import { toast } from "@/components/toaster";

/** True when the page was loaded before the app changed and calls a server action that no longer exists. */
export function isStaleAction(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  return /Server Action .*(not found|was not found)|Failed to find Server Action/i.test(msg);
}

/**
 * Call a server action from the browser. An out-of-date page reloads itself instead of crashing;
 * any other failure shows an error toast. Returns undefined when the call failed.
 */
export async function runAction<T>(fn: () => Promise<T>): Promise<T | undefined> {
  try {
    return await fn();
  } catch (e) {
    if (isStaleAction(e)) {
      toast({ kind: "error", title: "This page is out of date. Reloading…" });
      setTimeout(() => window.location.reload(), 1200);
    } else {
      toast({ kind: "error", title: "Something went wrong. Please try again." });
    }
    return undefined;
  }
}
