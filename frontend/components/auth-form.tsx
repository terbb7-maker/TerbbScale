"use client";

import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const search = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    const supabase = createClient();
    const result =
      mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({
            email,
            password,
            options: {
              data: { full_name: fullName },
              emailRedirectTo: `${location.origin}/auth/callback`,
            },
          });
    setLoading(false);
    if (result.error) {
      toast.error(result.error.message);
      return;
    }
    if (mode === "signup" && !result.data.session) {
      toast.success("Confira seu e-mail para confirmar o cadastro.");
      return;
    }
    router.replace(search.get("next") ?? "/app");
    router.refresh();
  }

  return (
    <form className="mt-9 space-y-4" onSubmit={submit}>
      {mode === "signup" && (
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-zinc-300">Seu nome</span>
          <input
            className="input"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            autoComplete="name"
            required
            maxLength={160}
          />
        </label>
      )}
      <label className="block">
          <span className="mb-2 block text-sm font-medium text-zinc-300">E-mail</span>
        <input
          className="input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
      </label>
      <label className="block">
          <span className="mb-2 block text-sm font-medium text-zinc-300">Senha</span>
        <input
          className="input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          minLength={8}
          required
        />
      </label>
      <button className="button-primary mt-3 min-h-12 w-full" disabled={loading} type="submit">
        {loading && <LoaderCircle className="animate-spin" size={17} />}
        {mode === "login" ? "Entrar" : "Criar conta"}
      </button>
      <p className="pt-3 text-center text-sm text-zinc-500">
        {mode === "login" ? "Ainda não tem uma conta? " : "Já tem uma conta? "}
        <Link className="font-medium text-violet-400 hover:text-violet-300" href={mode === "login" ? "/cadastro" : "/login"}>
          {mode === "login" ? "Cadastre-se" : "Entrar"}
        </Link>
      </p>
    </form>
  );
}
