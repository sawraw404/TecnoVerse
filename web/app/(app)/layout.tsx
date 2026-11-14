import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { api, currentMe } from "@/lib/api";
import type { User } from "@/lib/types";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await currentMe();
  if (!me) redirect("/login");
  const users = await api<User[]>("/users");
  return (
    <AppShell me={me} users={users}>
      {children}
    </AppShell>
  );
}
