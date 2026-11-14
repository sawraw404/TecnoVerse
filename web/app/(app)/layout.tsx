import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { currentMe } from "@/lib/api";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await currentMe();
  if (!me) redirect("/login");
  return <AppShell me={me}>{children}</AppShell>;
}
