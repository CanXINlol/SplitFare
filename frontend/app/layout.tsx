import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SplitFare - Mock flight combinations",
  description: "Compare protected and self-transfer itineraries using fictional mock data.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6">
          <Link href="/" className="text-xl font-black tracking-tight">SplitFare<span className="text-coral">.</span></Link>
          <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-bold uppercase tracking-widest">Mock demo</span>
        </header>
        {children}
      </body>
    </html>
  );
}
