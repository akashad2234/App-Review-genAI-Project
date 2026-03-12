"use client";

export default function SchedulesPage() {
  return (
    <main className="space-y-6">
      <section className="card">
        <div className="card-header">
          <h1 className="text-xl font-semibold tracking-tight">Schedules</h1>
          <p className="mt-1 text-sm text-slate-400">
            Auto-scrape, analyse, and email the weekly pulse on a fixed cadence.
          </p>
        </div>
        <div className="card-body text-sm text-slate-400">
          <p className="mb-3">
            Your backend is already configured with:
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>A local scheduler script that can run on a server or VM.</li>
            <li>
              A GitHub Actions workflow that runs the full pipeline every Sunday
              at 3:35 PM IST and emails the configured recipient.
            </li>
          </ul>
          <p className="mt-4 text-xs text-slate-500">
            This UI surface is a placeholder for future in-app schedule
            management, while the actual automation is handled by your
            scheduler and GitHub Actions.
          </p>
        </div>
      </section>
    </main>
  );
}

