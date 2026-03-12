"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";

type RunSummary = {
  run_id: string | null;
  status: string;
  period?: string | null;
  total_reviews?: number | null;
  started_at?: string;
  finished_at?: string;
  email_sent?: boolean;
  pulse_content?: string | null;
  eml_path?: string | null;
  top_themes?: string[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function DashboardPage() {
  const [health, setHealth] = useState<"ok" | "down" | "loading">("loading");
  const [latest, setLatest] = useState<RunSummary | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);
  const [loadingLatest, setLoadingLatest] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [reviewWindowDays, setReviewWindowDays] = useState<7 | 14 | 21 | 28>(7);
  const [maxReviews, setMaxReviews] = useState<number | "">(5000);
  const [recipientEmail, setRecipientEmail] = useState<string>("");
  const [recipientName, setRecipientName] = useState<string>("");

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`);
      if (!res.ok) {
        setHealth("down");
        return;
      }
      const data = (await res.json()) as { status: string };
      setHealth(data.status === "ok" ? "ok" : "down");
    } catch {
      setHealth("down");
    }
  };

  const fetchLatest = async () => {
    setLoadingLatest(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/pulse/latest`);
      if (!res.ok) {
        throw new Error(`Failed to fetch latest: ${res.statusText}`);
      }
      const data = (await res.json()) as RunSummary;
      setLatest(data);
      setShowReport(true);
    } catch (e: any) {
      setError(e?.message ?? "Failed to fetch latest run.");
    } finally {
      setLoadingLatest(false);
    }
  };

  const triggerRun = async (sendEmail: boolean) => {
    setLoadingRun(true);
    setError(null);
    setRunMessage(null);
    try {
      const weeks = reviewWindowDays / 7;
      const res = await fetch(`${API_BASE_URL}/api/pulse/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          weeks,
          max_reviews: maxReviews,
          send_email: sendEmail,
          recipient_email: recipientEmail.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Run failed (${res.status}): ${text || res.statusText}`
        );
      }
      await fetchLatest();
      setRunMessage(
        "Pipeline run completed. Use Load latest report to view the latest pulse and Download .eml for the draft email."
      );
    } catch (e: any) {
      setError(e?.message ?? "Failed to trigger pipeline run.");
    } finally {
      setLoadingRun(false);
    }
  };

  useEffect(() => {
    void fetchHealth();
  }, []);

  const hasReviews = latest && latest.total_reviews != null;
  const hasThemes = !!(latest && latest.top_themes && latest.top_themes.length);
  const hasReport = !!(latest && latest.pulse_content);
  const hasDraftEmail = !!(latest && latest.eml_path);

  const handleSendEmail = async (e: FormEvent) => {
    e.preventDefault();
    if (!recipientEmail.trim()) {
      setError("Recipient email is required to send.");
      return;
    }
    setLoadingEmail(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/pulse/latest/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient_email: recipientEmail.trim(),
          recipient_name: recipientName.trim() || undefined,
          force: false,
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Send email failed (${res.status}): ${text || res.statusText}`
        );
      }
      await fetchLatest();
    } catch (e: any) {
      setError(e?.message ?? "Failed to send email.");
    } finally {
      setLoadingEmail(false);
    }
  };

  const handleDownloadDraft = async () => {
    setError(null);
    try {
      const downloadRes = await fetch(`${API_BASE_URL}/api/files/latest-eml`);
      if (!downloadRes.ok) {
        const text = await downloadRes.text();
        if (downloadRes.status === 404) {
          throw new Error(
            "No draft email found for the latest run. Run the pipeline first."
          );
        }
        throw new Error(
          `Download failed (${downloadRes.status}): ${
            text || downloadRes.statusText
          }`
        );
      }
      const blob = await downloadRes.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "weekly-pulse-email.eml";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.message ?? "Failed to download draft email.");
    }
  };

  return (
    <main className="space-y-8">
      <section className="card mb-8">
        <div className="card-header pb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">
            Live · Play Store
          </p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight text-slate-50">
            Groww App
            <span className="block text-emerald-300">Review Pulse</span>
          </h1>
          <p className="mt-3 text-sm text-slate-400 max-w-xl">
            Scrapes live reviews, runs AI analysis, and delivers a one-page
            health pulse to your team.
          </p>
        </div>
        <div className="card-body pb-4">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="space-y-4">
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                  Review window
                </p>
                <div className="pill-toggle-group">
                  {[7, 14, 21, 28].map((days) => (
                    <button
                      key={days}
                      type="button"
                      className={`pill-toggle ${
                        reviewWindowDays === days ? "pill-toggle-active" : ""
                      }`}
                      onClick={() =>
                        setReviewWindowDays(days as 7 | 14 | 21 | 28)
                      }
                    >
                      {days}d
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                  Email recipients
                  <span className="ml-1 text-[0.65rem] font-normal text-slate-500">
                    (optional, comma-separated)
                  </span>
                </p>
                <input
                  type="email"
                  multiple
                  placeholder="pm@company.com, ceo@company.com"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-100 outline-none ring-0 focus:border-emerald-400"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-[0.75rem] text-slate-300">
                  Max reviews to fetch
                </label>
                <input
                  type="number"
                  className="w-full max-w-xs rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-emerald-400"
                  value={maxReviews === "" ? "" : maxReviews}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const value = e.target.value;
                    if (value === "") {
                      setMaxReviews("");
                      return;
                    }
                    const parsed = Number(value);
                    setMaxReviews(
                      Number.isNaN(parsed) ? 0 : Math.max(0, parsed),
                    );
                  }}
                  min={0}
                />
              </div>
            </div>
            <div className="flex flex-col items-stretch gap-3 md:w-64">
              <button
                className="btn btn-primary w-full py-2 text-sm"
                disabled={loadingRun}
                onClick={() => void triggerRun(true)}
              >
                {loadingRun
                  ? "Running pulse..."
                  : `Run ${reviewWindowDays}-Day Pulse`}
              </button>
              <p className="text-[0.7rem] text-slate-400">
                Pipeline: <span className="text-slate-200">Scrape</span>{" "}
                reviews · <span className="text-slate-200">Analyse</span>{" "}
                themes · <span className="text-slate-200">Report</span> one-page
                pulse · <span className="text-slate-200">Email</span> your
                team.
              </p>
              {runMessage && (
                <p className="text-[0.75rem] text-emerald-300">{runMessage}</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="card mb-6">
        <div className="card-header">
          <h2 className="text-lg font-medium">Pipeline status</h2>
          <p className="mt-1 text-xs text-slate-400">
            End-to-end health for the latest run.
          </p>
        </div>
        <div className="card-body flex flex-wrap items-center gap-2 text-xs">
          <span className={`badge ${hasReviews ? "badge-success" : "badge-pending"}`}>
            Reviews
          </span>
          <span className={`badge ${hasThemes ? "badge-success" : "badge-pending"}`}>
            Themes
          </span>
          <span className={`badge ${hasThemes ? "badge-success" : "badge-pending"}`}>
            Grouped
          </span>
          <span className={`badge ${hasReport ? "badge-success" : "badge-pending"}`}>
            Report
          </span>
          <span className={`badge ${hasDraftEmail ? "badge-success" : "badge-pending"}`}>
            Draft email
          </span>
          <span className="ml-2 text-[0.7rem] text-slate-400">
            Report date:{" "}
            {latest?.period ? latest.period : "No report yet"}
          </span>
        </div>
      </section>

      <section className="card mb-8">
        <div className="card-header flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-medium">View report</h2>
          </div>
          <button
            className="btn btn-outline text-xs"
            disabled={loadingLatest}
            onClick={() => {
              if (showReport) {
                setShowReport(false);
              } else {
                void fetchLatest();
              }
            }}
          >
            {loadingLatest
              ? "Loading..."
              : showReport
              ? "Hide report"
              : "Load latest report"}
          </button>
        </div>
        {showReport && (
          <div className="card-body">
            {latest && latest.pulse_content ? (
              <div className="pulse-content max-h-80 overflow-auto rounded-md border border-slate-700/60 bg-slate-950/50 p-3 text-xs">
                {latest.pulse_content}
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                No report loaded yet. Click "Load latest report" after running the pipeline.
              </p>
            )}
          </div>
        )}
      </section>

      <section className="card mb-10">
        <div className="card-header">
          <h2 className="text-lg font-medium">Download draft email</h2>
        </div>
        <div className="card-body text-xs text-slate-400">
          <p className="mb-2">
            Download the latest draft email as an <code>.eml</code> file that you
            can open in your email client.
          </p>
          <button
            type="button"
            className="border-none bg-transparent p-0 text-xs font-medium text-sky-400 underline underline-offset-2 disabled:text-slate-500"
            onClick={() => void handleDownloadDraft()}
          >
            Download .eml
          </button>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <h2 className="text-lg font-medium">Send email</h2>
          <p className="mt-1 text-xs text-slate-400">
            Send the latest report to an email address. Optional name adds
            "Hi name," at the start.
          </p>
        </div>
        <div className="card-body">
          <form
            onSubmit={handleSendEmail}
            className="grid gap-4 text-xs text-slate-300 md:grid-cols-[2fr_1.2fr_auto]"
          >
            <div>
              <label className="mb-1 block text-[0.75rem] text-slate-300">
                Recipient email
              </label>
              <input
                type="email"
                required
                placeholder="e.g. you@example.com"
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-emerald-400"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-[0.75rem] text-slate-300">
                Recipient name (optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Akash"
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-emerald-400"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="btn btn-primary text-xs"
                disabled={loadingEmail}
              >
                {loadingEmail ? "Sending..." : "Send email"}
              </button>
            </div>
          </form>
          <div className="mt-4 text-[0.75rem] text-slate-400">
            Report date: {latest?.period ?? "No report generated yet"}
          </div>
          {error && (
            <div className="mt-3 rounded-md border border-rose-500/40 bg-rose-950/40 px-3 py-2 text-xs text-rose-100">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

