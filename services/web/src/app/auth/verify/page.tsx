"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useSessionStore } from "@/store/session";
import { api } from "@/lib/api";

function VerifyInner() {
  const params = useSearchParams();
  const router = useRouter();
  const setJwt = useSessionStore((s) => s.setJwt);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      return;
    }

    api
      .verifyMagicLink(token)
      .then((res) => {
        setJwt(res.token);
        setStatus("success");
        setTimeout(() => router.push("/"), 1500);
      })
      .catch(() => setStatus("error"));
  }, [params, router, setJwt]);

  return (
    <div className="text-center">
      {status === "loading" && <p className="text-gray-500">Vérification en cours...</p>}
      {status === "success" && <p className="text-teal font-medium">Connecté ! Redirection...</p>}
      {status === "error" && (
        <div>
          <p className="text-red-500 font-medium">Lien invalide ou expiré.</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 text-sm text-teal underline"
          >
            Retour
          </button>
        </div>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-64px)]">
      <Suspense fallback={<p className="text-gray-500">Chargement...</p>}>
        <VerifyInner />
      </Suspense>
    </div>
  );
}
