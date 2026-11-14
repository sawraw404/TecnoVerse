"use client"; // error boundaries are client components

import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui";

export default function ErrorView({ error, retry }: { error: unknown; retry: () => void }) {
  const message = error instanceof Error ? error.message : "Unknown error";
  return (
    <div className="mx-4 mt-10 max-w-lg rounded-lg sm:mx-auto border border-red/25 bg-surface p-6 shadow-sm">
      <div className="mb-3 grid size-10 place-items-center rounded-full bg-red-soft text-red">
        <AlertTriangle className="size-5" aria-hidden />
      </div>
      <h1 className="text-lg font-semibold">This page could not load</h1>
      <p className="mt-1 text-sm leading-6 text-text-2">
        {/* production builds hide server messages; the API-not-running case is the common one */}
        {/Server Action/i.test(message)
          ? "This page is out of date because the app was updated. Reload the page to continue."
          : message.includes("not reachable") || message.includes("Server Components")
          ? "The TecnoVerse API may not be running. Start it from the repo root with: uvicorn api:app --app-dir tecnoverse"
          : message}
      </p>
      <Button variant="primary" className="mt-5" onClick={() => (/Server Action/i.test(message) ? window.location.reload() : retry())}>
        <RotateCw className="size-4" aria-hidden /> Try again
      </Button>
    </div>
  );
}
