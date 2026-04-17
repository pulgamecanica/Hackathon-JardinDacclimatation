import type { Metadata } from "next";
import { Cormorant_Garamond, Outfit } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/navbar";
import SessionProvider from "@/components/session-provider";

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Pavo — Jardin d'Acclimatation",
  description: "Planifiez votre visite au Jardin d'Acclimatation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className={`${cormorant.variable} ${outfit.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#FAFAFA] text-foreground" style={{ fontFamily: "var(--font-outfit), sans-serif" }}>
        <SessionProvider>
          <Navbar />
          <main className="flex-1 pt-[70px]">{children}</main>
        </SessionProvider>
      </body>
    </html>
  );
}
