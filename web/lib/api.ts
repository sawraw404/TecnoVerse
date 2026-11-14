// Server-side access to the Python API (tecnoverse/api.py). Only the Next server calls it; the browser
// never sees the API or another company's data. The SIMULATED login is a cookie holding a user id.
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
export const USER_COOKIE = "tv_user";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function currentUserId(): Promise<string | undefined> {
  return (await cookies()).get(USER_COOKIE)?.value;
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const userId = (await currentUserId()) ?? "guest";
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: init.method ?? "GET",
      headers: { "X-User-Id": userId, "Content-Type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, `The TecnoVerse API is not reachable at ${API_URL}. Start it with: uvicorn api:app --app-dir tecnoverse`);
  }
  if (!res.ok) {
    const detail = await res
      .json()
      .then((j: { detail?: unknown }) => (typeof j.detail === "string" ? j.detail : res.statusText))
      .catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}
