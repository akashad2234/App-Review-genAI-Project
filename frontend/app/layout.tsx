import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { headers } from "next/headers";

export const metadata = {
  title: "Groww App Review Pulse",
  description:
    "Scrapes live reviews, runs AI analysis, and delivers a one-page health pulse.",
};

function getActivePath(): string {
  // Best-effort detection of current pathname on the server
  try {
    const h = headers();
    const path = h.get("x-invoke-path") || h.get("x-pathname");
    return path || "/";
  } catch {
    return "/";
  }
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const activePath = getActivePath();

  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-6">
          <header className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-400/90 text-slate-950 font-bold text-lg shadow-lg shadow-emerald-500/40">
                G
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold tracking-wide text-emerald-300">
                  Groww Pulse
                </div>
                <div className="text-xs text-slate-400">
                  Play Store review health dashboard
                </div>
              </div>
            </div>
            <nav className="flex items-center gap-6 text-sm">
              <Link
                href="/"
                className={`nav-tab ${
                  activePath === "/" ? "nav-tab-active" : ""
                }`}
              >
                Analyse
              </Link>
              <Link
                href="/schedules"
                className={`nav-tab ${
                  activePath?.startsWith("/schedules") ? "nav-tab-active" : ""
                }`}
              >
                Schedules
              </Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

