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

/** SIMULATED login: remember the chosen user in a cookie, then land on that role's start page. */
export async function logIn(formData: FormData) {
  const id = String(formData.get("user") ?? "");
  const users = await api<User[]>("/users");
  const user = users.find((u) => u.id === id);
  if (!user) return;
  (await cookies()).set(USER_COOKIE, user.id, { httpOnly: true, sameSite: "lax", path: "/" });
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

export async function sendFeedback(opportunityId: string, kind: "up" | "down") {
  try {
    await api("/feedback", { method: "POST", body: { opportunity_id: opportunityId, kind } });
    revalidatePath("/dashboard");
    return { ok: true } as const;
  } catch (e) {
    return failure(e);
  }
}

export type ChatResult = ChatReply | { label: GuardLabel; text: string; sources: []; error: true };

export async function sendChat(message: string, history: { role: "user" | "assistant"; text: string }[]): Promise<ChatResult> {
  try {
    return await api<ChatReply>("/chat", { method: "POST", body: { message, history } });
  } catch (e) {
    return { label: "unclear", text: failure(e).error, sources: [], error: true };
  }
}
