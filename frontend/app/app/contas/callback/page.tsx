"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

function Callback() {
  const search = useSearchParams();
  const router = useRouter();
  const started = useRef(false);
  const code = search.get("code");
  const state = search.get("state");
  const [message, setMessage] = useState(
    code && state
      ? "Finalizando conexão segura…"
      : "O Instagram não retornou os dados necessários.",
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!code || !state) return;
    api("/accounts/oauth/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    })
      .then(() => {
        const returnTo = sessionStorage.getItem("terbb-account-connect-return");
        sessionStorage.removeItem("terbb-account-connect-return");
        router.replace(returnTo?.startsWith("/app/contas") ? returnTo : "/app/contas");
      })
      .catch((error) => setMessage(error.message));
  }, [code, router, state]);

  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div className="panel max-w-md p-8 text-center">
        <LoaderCircle className="mx-auto animate-spin text-violet-400" size={28} />
        <p className="mt-5 text-sm text-zinc-400">{message}</p>
      </div>
    </div>
  );
}

export default function InstagramCallbackPage() {
  return <Suspense><Callback /></Suspense>;
}
