import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, currentUserId } from "@/lib/api";
import type { Me } from "@/lib/types";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  if (!(await currentUserId())) redirect("/login");
  const me = await api<Me>("/me");
  return <AppShell me={me}>{children}</AppShell>;
}
