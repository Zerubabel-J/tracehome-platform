// Small building blocks shared by every page.
import type { ReactNode } from "react";
import { Link } from "react-router";
import { initials, PERSONAS, type Persona } from "../roles";

export function Avatar({ name, persona, size = 36 }: { name: string; persona: Persona; size?: number }) {
  return (
    <span className={`avatar p-${persona}`} style={{ width: size, height: size, fontSize: size * 0.38 }} aria-hidden>
      {initials(name)}
    </span>
  );
}

export function RoleBadge({ persona }: { persona: Persona }) {
  return <span className={`badge p-${persona}`}>{PERSONAS[persona].label}</span>;
}

const PILL_LABEL: Record<string, string> = {
  checking: "Checking",
  approved: "Approved",
  under_review: "Under review",
  rejected: "Rejected",
  submitted: "Waiting for approval",
  removed: "Removed",
  open: "Open",
  closed: "Closed",
};

export function StatusPill({ status }: { status: string }) {
  return <span className={`pill s-${status}`}>{PILL_LABEL[status] ?? status}</span>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

/** Shown when a page needs a role the visitor doesn't have. */
export function NeedsRole({ who, what }: { who: string; what: string }) {
  return (
    <div className="gate">
      <h1>{what}</h1>
      <p>
        This page is for <strong>{who}</strong>. Pick a made-up user to see it.
      </p>
      <Link to="/demo" className="btn">
        Choose a demo user
      </Link>
    </div>
  );
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [
    [86400, "day"],
    [3600, "hour"],
    [60, "minute"],
  ];
  for (const [size, name] of units) {
    if (seconds >= size) {
      const n = Math.floor(seconds / size);
      return `${n} ${name}${n === 1 ? "" : "s"} ago`;
    }
  }
  return "just now";
}
