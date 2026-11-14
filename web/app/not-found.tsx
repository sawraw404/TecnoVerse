import { Compass } from "lucide-react";
import Link from "next/link";
import { buttonClass } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center px-4">
      <div className="text-center">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-surface-2 text-text-3">
          <Compass className="size-6" aria-hidden />
        </div>
        <h1 className="text-xl font-semibold">Page not found</h1>
        <p className="mt-1 text-sm text-text-2">This page does not exist, or it is not available for the user you are logged in as.</p>
        <Link href="/" className={buttonClass("primary", "md", "mt-5")}>
          Go to start
        </Link>
      </div>
    </main>
  );
}
