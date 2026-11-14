import { redirect } from "next/navigation";
import { api, currentUserId } from "@/lib/api";
import type { Me } from "@/lib/types";

export default async function Home() {
  if (!(await currentUserId())) redirect("/login");
  const { user } = await api<Me>("/me");
  redirect(user.role === "staff" ? "/staff" : user.role === "member" ? "/profile" : "/dashboard");
}
