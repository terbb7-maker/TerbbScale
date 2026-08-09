"use client";

import {
  Bell,
  BookImage,
  Camera,
  ChevronRight,
  CircleUserRound,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Megaphone,
  Menu,
  Network,
  Settings,
  Shield,
  Trophy,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { BrandLogo } from "@/components/brand-logo";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { UserProfile } from "@/lib/types";

const groups = [
  {
    label: "Principal",
    links: [
      { href: "/app", label: "Dashboard", icon: LayoutDashboard },
      { href: "/app/campanhas", label: "Campanhas", icon: Megaphone },
    ],
  },
  {
    label: "Gerenciar",
    links: [
      { href: "/app/contas", label: "Contas", icon: Camera },
      { href: "/app/biblioteca", label: "Biblioteca", icon: BookImage },
      { href: "/app/proxies", label: "Proxies", icon: Network },
    ],
  },
  {
    label: "Sistema",
    links: [
      { href: "/app/logs", label: "Histórico", icon: ListChecks },
      { href: "/app/configuracoes", label: "Configurações", icon: Settings },
    ],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<UserProfile>("/auth/me")
      .then(setProfile)
      .catch((error) => toast.error(error.message))
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  if (loading) {
    return <div className="grid min-h-screen place-items-center"><div className="size-8 animate-spin rounded-full border-2 border-violet-950 border-t-violet-400" /></div>;
  }

  if (profile && profile.status !== "active") {
    return (
      <main className="auth-background grid min-h-screen place-items-center px-6">
        <section className="panel max-w-lg p-8 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-xl bg-amber-400/10 text-amber-400"><Shield size={23} /></span>
          <p className="eyebrow mt-6">Acesso em análise</p>
          <h1 className="mt-2 text-2xl font-semibold">Seu cadastro está pendente</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">Assim que um administrador aprovar seu acesso, o painel será liberado.</p>
          <button className="button-secondary mt-7" onClick={logout}>Sair da conta</button>
        </section>
      </main>
    );
  }

  const admin = profile?.permissions.includes("admin:users");
  const shortName = profile?.full_name?.split(" ")[0] ?? "Conta";

  return (
    <div className="min-h-screen md:pl-[264px]">
      <aside className={`fixed inset-y-0 left-0 z-50 w-[264px] border-r border-white/[0.06] bg-[#0d0b14]/98 p-4 shadow-2xl transition-transform md:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between px-2 py-2">
            <BrandLogo />
            <button aria-label="Fechar menu" className="text-zinc-500 md:hidden" onClick={() => setMobileOpen(false)}><X size={20} /></button>
          </div>

          <nav className="mt-7 space-y-6">
            {groups.map((group) => (
              <div key={group.label}>
                <p className="eyebrow mb-2 px-3">{group.label}</p>
                <div className="space-y-1">
                  {group.links.map(({ href, label, icon: Icon }) => {
                    const active = href === "/app" ? pathname === href : pathname.startsWith(href);
                    return (
                      <Link
                        className={`relative flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium ${active ? "bg-violet-500/12 text-violet-200 shadow-[inset_0_0_0_1px_rgba(159,87,255,.14)]" : "text-zinc-500 hover:bg-white/[0.035] hover:text-zinc-200"}`}
                        href={href}
                        key={href}
                        onClick={() => setMobileOpen(false)}
                      >
                        {active && <span className="absolute -left-4 h-6 w-[3px] rounded-r bg-violet-500 shadow-[0_0_16px_#8b3dff]" />}
                        <Icon size={17} className={active ? "text-violet-400" : ""} />
                        <span className="flex-1">{label}</span>
                        {active && <ChevronRight size={13} className="text-violet-500" />}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
            {admin && (
              <div>
                <p className="eyebrow mb-2 px-3">Administração</p>
                <Link className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium ${pathname.startsWith("/app/admin") ? "bg-violet-500/12 text-violet-200" : "text-zinc-500 hover:bg-white/[0.035] hover:text-zinc-200"}`} href="/app/admin" onClick={() => setMobileOpen(false)}>
                  <Shield size={17} /> Painel admin
                </Link>
              </div>
            )}
          </nav>

          <div className="mt-auto">
            <Link
              className={`group mb-3 flex items-center gap-3 rounded-2xl border p-4 ${pathname.startsWith("/app/ranking") ? "border-violet-400/25 bg-violet-500/12" : "border-violet-400/10 bg-[linear-gradient(145deg,rgba(112,31,219,.12),rgba(255,255,255,.015))] hover:border-violet-400/25 hover:bg-violet-500/10"}`}
              href="/app/ranking"
              onClick={() => setMobileOpen(false)}
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-500/15 text-violet-300"><Trophy size={18} /></span>
              <span className="min-w-0 flex-1"><span className="block text-xs font-semibold text-violet-200">Ranking mensal</span><span className="mt-1 block text-[11px] text-zinc-500">Veja os melhores do mês</span></span>
              <ChevronRight size={15} className="text-violet-500 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <button className="flex w-full items-center gap-3 rounded-xl border-t border-white/[0.06] px-3 py-3 text-left text-sm hover:bg-white/[0.035]" onClick={logout}>
              <span className="grid size-9 place-items-center rounded-xl bg-violet-500/10 text-violet-400"><CircleUserRound size={18} /></span>
              <span className="min-w-0 flex-1"><span className="block truncate font-medium text-zinc-200">{profile?.full_name ?? shortName}</span><span className="block truncate text-[11px] text-zinc-600">{profile?.email}</span></span>
              <LogOut size={15} className="text-zinc-600" />
            </button>
          </div>
        </div>
      </aside>

      {mobileOpen && <button aria-label="Fechar menu" className="fixed inset-0 z-40 bg-black/75 backdrop-blur-sm md:hidden" onClick={() => setMobileOpen(false)} />}

      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/[0.055] bg-[#090811]/85 px-4 backdrop-blur-xl md:px-7">
        <button aria-label="Abrir menu" className="grid size-10 place-items-center rounded-xl border border-white/[0.07] text-zinc-400 md:hidden" onClick={() => setMobileOpen(true)}><Menu size={20} /></button>
        <p className="hidden text-xs text-zinc-600 md:block">Olá, <span className="text-zinc-300">{shortName}</span></p>
        <div className="ml-auto flex items-center gap-2">
          <Link aria-label="Notificações" className="relative grid size-10 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-zinc-500 hover:text-white" href="/app/notificacoes"><Bell size={17} /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-violet-500" /></Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1600px] p-4 md:p-7 xl:p-8">{children}</main>
    </div>
  );
}
