import { redirect } from "next/navigation";
import { currentMe } from "@/lib/api";

export default async function Home() {
  const me = await currentMe();
  if (!me) redirect("/login");
  redirect(me.user.role === "staff" ? "/staff" : me.user.role === "member" ? "/profile" : "/dashboard");
}
