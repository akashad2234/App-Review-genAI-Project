import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Groww App Review Pulse",
  description:
    "Scrapes live reviews, runs AI analysis, and delivers a one-page health pulse.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <div className="flex min-h-screen items-center justify-center">
          <div className="w-full max-w-5xl px-4 py-8">{children}</div>
        </div>
      </body>
    </html>
  );
}

