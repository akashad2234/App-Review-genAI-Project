"use client";

import { useState } from "react";

export default function SchedulesPage() {
  const [showModal, setShowModal] = useState(false);

  return (
    <main className="space-y-8 text-center">
      <section className="card">
        <div className="card-header flex items-center justify-between">
          <div className="text-left">
            <h1 className="text-2xl font-semibold tracking-tight text-[#04ad83]">
              Scheduled Reports
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Auto-scrape, analyse, and email the pulse on your schedule.
            </p>
          </div>
          <button
            className="btn btn-primary text-xs"
            type="button"
            onClick={() => setShowModal(true)}
          >
            + New Schedule
          </button>
        </div>
        <div className="card-body">
          <div className="mx-auto max-w-md rounded-xl bg-slate-950/40 px-6 py-10 text-center">
            <p className="text-sm font-medium text-slate-200">
              No schedules yet
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Create one to automatically send weekly pulses.
            </p>
            <button
              className="btn btn-primary mt-5 text-xs"
              type="button"
              onClick={() => setShowModal(true)}
            >
              + Create first schedule
            </button>
          </div>
        </div>
      </section>

      {showModal && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-950/95 text-left shadow-2xl">
            <div className="border-b border-slate-800 px-5 py-4">
              <h2 className="text-lg font-semibold text-[#04ad83]">
                New Schedule
              </h2>
              <p className="mt-1 text-xs text-slate-400">
                Configures when the backend scheduler / GitHub Actions run the
                weekly pulse and send the email.
              </p>
            </div>
            <div className="space-y-4 px-5 py-4 text-xs text-slate-300">
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-[0.7rem] font-semibold text-[#04ad83]">
                    Frequency
                  </p>
                  <div className="pill-toggle-group">
                    <button className="pill-toggle pill-toggle-active" type="button">
                      Weekly
                    </button>
                  </div>
                </div>
                <div>
                  <p className="mb-1 text-[0.7rem] font-semibold text-[#04ad83]">
                    Day of week
                  </p>
                  <select className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-[#04ad83]">
                    <option>Sunday</option>
                    <option>Monday</option>
                    <option>Tuesday</option>
                    <option>Wednesday</option>
                    <option>Thursday</option>
                    <option>Friday</option>
                    <option>Saturday</option>
                  </select>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-[0.7rem] font-semibold text-[#04ad83]">
                    Time
                  </p>
                  <input
                    type="time"
                    defaultValue="15:35"
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-[#04ad83]"
                  />
                </div>
                <div>
                  <p className="mb-1 text-[0.7rem] font-semibold text-[#04ad83]">
                    Review window
                  </p>
                  <div className="pill-toggle-group">
                    {["7d", "14d", "21d", "28d"].map((label) => (
                      <button
                        key={label}
                        type="button"
                        className={`pill-toggle ${
                          label === "7d" ? "pill-toggle-active" : ""
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div>
                <p className="mb-1 text-[0.7rem] font-semibold text-[#04ad83]">
                  Recipients (comma-separated)
                </p>
                <input
                  type="email"
                  multiple
                  placeholder="pm@company.com, ceo@company.com"
                  className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-[#04ad83]"
                />
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3 text-xs">
              <button
                type="button"
                className="btn-outline rounded-full px-4 py-1"
                onClick={() => setShowModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary px-6 py-1.5 text-xs"
                onClick={() => setShowModal(false)}
              >
                Save Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

