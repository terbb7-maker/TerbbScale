import type { Metadata } from "next";
import { Toaster } from "sonner";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Terbb Scale", template: "%s · Terbb Scale" },
  description: "Gerencie e publique conteúdo no Instagram em escala.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <Providers>{children}</Providers>
        <Toaster theme="dark" richColors position="top-right" />
      </body>
    </html>
  );
}
