import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Groww Weekly Review Pulse",
  description: "Dashboard to run the Groww review pulse pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <div className="mx-auto max-w-5xl px-4 py-8">{children}</div>
      </body>
    </html>
  );
}

