import { BarChart3, CheckCircle2, Layers3, ShieldCheck } from "lucide-react";
import { Suspense } from "react";

import { AuthForm } from "@/components/auth-form";
import { BrandLogo } from "@/components/brand-logo";

export function AuthShell({ mode }: { mode: "login" | "signup" }) {
  const login = mode === "login";
  return (
    <main className="auth-background grid min-h-screen lg:grid-cols-[1.05fr_.95fr]">
      <aside className="relative hidden overflow-hidden border-r border-white/[0.06] p-10 lg:flex lg:flex-col">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_32%_30%,rgba(128,55,255,.2),transparent_32%)]" />
        <div className="relative z-10"><BrandLogo /></div>
        <div className="relative z-10 my-auto max-w-xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-300">
            <span className="size-1.5 rounded-full bg-violet-400 shadow-[0_0_12px_#a78bfa]" />
            Sua operação em um só lugar
          </span>
          <h2 className="mt-7 text-5xl font-semibold leading-[1.05] tracking-[-0.045em] text-white">
            Publique mais.<br />Gerencie melhor.<br /><span className="gradient-text">Cresça em escala.</span>
          </h2>
          <p className="mt-6 max-w-lg text-base leading-7 text-zinc-400">
            Contas, mídias, campanhas e resultados organizados para você entender tudo em segundos.
          </p>
          <div className="mt-10 grid max-w-lg grid-cols-2 gap-3">
            {[
              [Layers3, "Campanhas simples"],
              [BarChart3, "Métricas ao vivo"],
              [ShieldCheck, "API oficial"],
              [CheckCircle2, "Controle completo"],
            ].map(([Icon, label]) => {
              const ItemIcon = Icon as typeof Layers3;
              return <div className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.025] p-3.5 text-sm text-zinc-300" key={String(label)}><ItemIcon size={17} className="text-violet-400" />{String(label)}</div>;
            })}
          </div>
        </div>
        <p className="relative z-10 text-xs text-zinc-600">Terbb Scale · Instagram Platform API</p>
      </aside>

      <section className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-[420px]">
          <div className="mb-12 lg:hidden"><BrandLogo /></div>
          <p className="eyebrow">{login ? "Bem-vindo de volta" : "Comece agora"}</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
            {login ? "Entre na sua conta" : "Crie sua conta"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            {login
              ? "Acesse seu painel e continue de onde parou."
              : "Cadastre-se. Seu acesso será liberado após aprovação."}
          </p>
          <Suspense><AuthForm mode={mode} /></Suspense>
          <p className="mt-8 text-center text-xs text-zinc-600">
            Ao continuar, você concorda com o uso seguro da plataforma.
          </p>
        </div>
      </section>
    </main>
  );
}
