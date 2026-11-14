"use client";

import { Bookmark, BookmarkCheck, Check, Copy, MessageSquareText, ThumbsDown, ThumbsUp } from "lucide-react";
import Link from "next/link";
import { useState, useTransition } from "react";
import { sendFeedback } from "@/app/actions";
import { toast } from "@/components/toaster";
import { Button, buttonClass, Spinner } from "@/components/ui";
import { cx } from "@/lib/format";

/** Thumbs up/down (re-rank), save for later, and "Ask about this" (opens the Assistant on this opportunity). */
export function CardActions({
  opportunityId,
  title,
  vote,
  saved,
}: {
  opportunityId: string;
  title: string;
  vote: "up" | "down" | null;
  saved: boolean;
}) {
  const [pending, start] = useTransition();
  const [which, setWhich] = useState<string | null>(null);
  const send = (kind: "up" | "down" | "saved" | "unsaved") => {
    setWhich(kind);
    start(async () => {
      const r = await sendFeedback(opportunityId, kind);
      const done = {
        up: "Noted: more like this. Ranking updated.",
        down: "Noted: less like this. Ranking updated.",
        saved: "Saved. Find it under the Saved tab.",
        unsaved: "Removed from Saved.",
      }[kind];
      toast(r.ok ? { kind: "success", title: done } : { kind: "error", title: r.error });
    });
  };
  const busy = (k: string) => pending && which === k;
  return (
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label={`Actions for ${title}`}>
      <Link href={`/chat?about=${encodeURIComponent(opportunityId)}`} className={buttonClass("ghost", "sm")} title="Ask the assistant about this">
        <MessageSquareText className="size-4" aria-hidden />
        <span>Ask about this</span>
      </Link>
      <Button
        variant="ghost"
        size="sm"
        disabled={pending}
        aria-pressed={saved}
        onClick={() => send(saved ? "unsaved" : "saved")}
        title={saved ? "Remove from Saved" : "Save for later"}
        className={cx(saved && "text-primary-text")}
      >
        {busy("saved") || busy("unsaved") ? <Spinner /> : saved ? <BookmarkCheck className="size-4" aria-hidden /> : <Bookmark className="size-4" aria-hidden />}
        <span className="sr-only sm:not-sr-only">{saved ? "Saved" : "Save"}</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={pending}
        aria-pressed={vote === "up"}
        onClick={() => send("up")}
        title="More like this"
        className={cx(vote === "up" && "bg-green-soft text-green")}
      >
        {busy("up") ? <Spinner /> : <ThumbsUp className="size-4" aria-hidden />}
        <span className="sr-only">Relevant</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={pending}
        aria-pressed={vote === "down"}
        onClick={() => send("down")}
        title="Less like this"
        className={cx(vote === "down" && "bg-red-soft text-red")}
      >
        {busy("down") ? <Spinner /> : <ThumbsDown className="size-4" aria-hidden />}
        <span className="sr-only">Not relevant</span>
      </Button>
    </div>
  );
}

export function CopyText({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {
          toast({ kind: "error", title: "Could not copy. Select the text and copy it manually." });
        }
      }}
    >
      {copied ? <Check className="size-4 text-green" aria-hidden /> : <Copy className="size-4" aria-hidden />}
      {copied ? "Copied" : label}
    </Button>
  );
}
