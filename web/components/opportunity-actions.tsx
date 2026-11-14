"use client";

import { Check, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState, useTransition } from "react";
import { sendFeedback } from "@/app/actions";
import { toast } from "@/components/toaster";
import { Button, Spinner } from "@/components/ui";

export function FeedbackButtons({ opportunityId, title }: { opportunityId: string; title: string }) {
  const [pending, start] = useTransition();
  const [which, setWhich] = useState<"up" | "down" | null>(null);
  const vote = (kind: "up" | "down") => {
    setWhich(kind);
    start(async () => {
      const r = await sendFeedback(opportunityId, kind);
      toast(r.ok ? { kind: "success", title: kind === "up" ? "Noted: more like this. Ranking updated." : "Noted: less like this. Ranking updated." } : { kind: "error", title: r.error });
    });
  };
  return (
    <div className="flex items-center gap-1" role="group" aria-label={`Feedback on ${title}`}>
      <Button variant="ghost" size="sm" disabled={pending} onClick={() => vote("up")} title="More like this">
        {pending && which === "up" ? <Spinner /> : <ThumbsUp className="size-4" aria-hidden />}
        <span className="sr-only sm:not-sr-only">Relevant</span>
      </Button>
      <Button variant="ghost" size="sm" disabled={pending} onClick={() => vote("down")} title="Less like this">
        {pending && which === "down" ? <Spinner /> : <ThumbsDown className="size-4" aria-hidden />}
        <span className="sr-only sm:not-sr-only">Not relevant</span>
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
