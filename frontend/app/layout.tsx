import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { CityCatalogProvider } from "@/lib/city-catalog";
import { I18nProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "SplitFare — protected fares vs self-transfer",
  description: "Compare protected and self-transfer flight combinations with transparent risk.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><I18nProvider><CityCatalogProvider><AppShell>{children}</AppShell></CityCatalogProvider></I18nProvider></body>
    </html>
  );
}
