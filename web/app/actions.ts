"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { api, ApiError, USER_COOKIE } from "@/lib/api";
import type { ChatReply, GuardLabel, Move, PriorityType, User } from "@/lib/types";

export type EditResult = { ok: true; moves: Move[] } | { ok: false; error: string };

function failure(e: unknown): { ok: false; error: string } {
  return { ok: false, error: e instanceof ApiError ? e.message : "Something went wrong. Please try again." };
}

/** Pages each role may open. Profile is for companies only, Ecosystem for staff only. */
function allowed(role: User["role"], path: string): boolean {
  if (["/dashboard", "/chat", "/about"].includes(path)) return true;
  return (path === "/profile" && role === "member") || (path === "/staff" && role === "staff");
}

/** SIMULATED login: remember the chosen user in a cookie. The sidebar switcher passes the current page
 *  as `next`, so switching company keeps you on the same page when the new user may see it. */
export async function logIn(formData: FormData) {
  const id = String(formData.get("user") ?? "");
  const next = String(formData.get("next") ?? "");
  const users = await api<User[]>("/users");
  const user = users.find((u) => u.id === id);
  if (!user) return;
  (await cookies()).set(USER_COOKIE, user.id, { httpOnly: true, sameSite: "lax", path: "/" });
  if (allowed(user.role, next)) redirect(next);
  redirect(user.role === "staff" ? "/staff" : user.role === "member" ? "/profile" : "/dashboard");
}

export async function logOut() {
  (await cookies()).delete(USER_COOKIE);
  redirect("/login");
}

async function edit(path: string, method: string, body?: unknown): Promise<EditResult> {
  try {
    const moves = await api<Move[]>(path, { method, body });
    revalidatePath("/", "layout");
    return { ok: true, moves };
  } catch (e) {
    return failure(e);
  }
}

export async function confirmItem(id: string) {
  return edit(`/profile/items/${encodeURIComponent(id)}/confirm`, "POST");
}

export async function removeItem(id: string) {
  return edit(`/profile/items/${encodeURIComponent(id)}/remove`, "POST");
}

export async function correctItem(id: string, value: string) {
  if (!value.trim()) return { ok: false, error: "Enter the corrected value." } as const;
  return edit(`/profile/items/${encodeURIComponent(id)}/correct`, "POST", { value });
}

export async function addItem(field: string, value: string) {
  if (!value.trim()) return { ok: false, error: "Enter a value." } as const;
  return edit("/profile/items", "POST", { field, value });
}

export async function setPriorities(types: PriorityType[]) {
  return edit("/profile/priorities", "PUT", { types });
}

export async function rebuildProfile(): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await api("/profile/rebuild", { method: "POST" });
    revalidatePath("/", "layout");
    return { ok: true };
  } catch (e) {
    return failure(e);
  }
}

export async function setVisibility(id: string, visibility: "public" | "private") {
  return edit(`/profile/items/${encodeURIComponent(id)}/visibility`, "POST", { visibility });
}

export async function sendFeedback(opportunityId: string, kind: "up" | "down" | "saved" | "unsaved") {
  try {
    await api("/feedback", { method: "POST", body: { opportunity_id: opportunityId, kind } });
    revalidatePath("/dashboard");
    return { ok: true } as const;
  } catch (e) {
    return failure(e);
  }
}

export type ChatResult = ChatReply | { session_id: null; label: GuardLabel; text: string; sources: []; error: true };

/** One turn. The conversation's earlier turns are read from storage on the server, not sent from here. */
export async function sendChat(message: string, sessionId: string | null, opportunityId: string | null): Promise<ChatResult> {
  try {
    const r = await api<ChatReply>("/chat", {
      method: "POST",
      body: { message, session_id: sessionId, opportunity_id: sessionId ? null : opportunityId },
    });
    revalidatePath("/chat");
    return r;
  } catch (e) {
    return { session_id: null, label: "unclear", text: failure(e).error, sources: [], error: true };
  }
}
