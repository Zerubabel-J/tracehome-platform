import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { Empty, NeedsRole, RoleBadge, Stat, StatusPill, timeAgo } from "../components/ui";
import { shortName, type Persona } from "../roles";
import type { ModerationSummary, ReviewCase } from "../types";

// Principle 4: automation decides the clear cases; a person decides the doubtful ones.
export function ModerationPage() {
  const { me } = useAuth();
  const [tab, setTab] = useState<"open" | "closed">("open");
  const [cases, setCases] = useState<ReviewCase[] | null>(null);
  const [summary, setSummary] = useState<ModerationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [list, counts] = await Promise.all([api.reviewCases(tab), api.moderationSummary()]);
      setCases(list);
      setSummary(counts);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [tab]);

  useEffect(() => {
    if (me?.role === "moderator") void load();
  }, [me, load]);

  if (me?.role !== "moderator") {
    return <NeedsRole who="TraceHome moderators" what="Moderation" />;
  }

  return (
    <>
      <section className="page-head">
        <div>
          <h1>Moderation</h1>
          <p className="muted">
            Photos the automatic checks weren't sure about. They stay private in <code>held/</code> until you decide.
          </p>
        </div>
      </section>

      <div className="stats">
        <Stat label="Waiting for you" value={summary?.open ?? "–"} hint="oldest first" />
        <Stat label="Approved" value={summary?.approved ?? "–"} hint="published to the photos bucket" />
        <Stat label="Rejected" value={summary?.rejected ?? "–"} hint="the advertiser sees the reason" />
      </div>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "open"} className={tab === "open" ? "active" : ""} onClick={() => setTab("open")}>
          Queue {summary ? `(${summary.open})` : ""}
        </button>
        <button role="tab" aria-selected={tab === "closed"} className={tab === "closed" ? "active" : ""} onClick={() => setTab("closed")}>
          Decided
        </button>
      </div>

      {error && <p className="alert error">{error}</p>}
      {cases === null && !error && <p className="muted">Loading…</p>}
      {cases?.length === 0 &&
        (tab === "open" ? (
          <Empty title="Queue is empty">Nothing is waiting. New flagged photos appear here automatically.</Empty>
        ) : (
          <Empty title="No decisions yet">Decide a case from the queue and it shows up here.</Empty>
        ))}

      <div className="cases">
        {cases?.map((c) => (tab === "open" ? <OpenCase key={c.id} item={c} onDone={load} /> : <ClosedCase key={c.id} item={c} />))}
      </div>
    </>
  );
}

function OpenCase({ item, onDone }: { item: ReviewCase; onDone: () => Promise<void> }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approved" | "rejected") {
    setBusy(true);
    setError(null);
    try {
      await api.decide(item.id, decision, note.trim() || null);
      await onDone();
    } catch (e) {
      setError((e as ApiError).message);
      setBusy(false);
    }
  }

  return (
    <article className="case">
      <div className="case-media">
        {item.preview_url ? <img src={item.preview_url} alt="Flagged upload" /> : <div className="no-photo">No preview</div>}
        <span className="case-lock" title="Private file, shown through a 5-minute signed link">
          Private · 5-min link
        </span>
      </div>
      <div className="case-body">
        <div className="case-top">
          <StatusPill status="under_review" />
          <span className="muted small">Case #{item.id} · flagged {timeAgo(item.created_at)}</span>
        </div>
        <p className="case-reason">{item.reason}</p>
        <dl className="case-facts">
          <dt>Listing</dt>
          <dd>
            <Link to={`/listings/${item.listing_id}`}>{item.listing_title}</Link>
          </dd>
          <dt>Advertiser</dt>
          <dd>
            {shortName(item.advertiser_name)} <RoleBadge persona={item.advertiser_kind as Persona} />
          </dd>
        </dl>
        <label className="field">
          <span>Reason for the advertiser (needed if you reject)</span>
          <input value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} placeholder="e.g. The photo shows a phone number" />
        </label>
        {error && <p className="alert error">{error}</p>}
        <div className="case-actions">
          <button className="btn ok" disabled={busy} onClick={() => void decide("approved")}>
            Approve and publish
          </button>
          <button className="btn danger" disabled={busy || !note.trim()} onClick={() => void decide("rejected")}>
            Reject
          </button>
        </div>
      </div>
    </article>
  );
}

function ClosedCase({ item }: { item: ReviewCase }) {
  return (
    <article className="case closed">
      <div className="case-body">
        <div className="case-top">
          <StatusPill status={item.decision ?? "closed"} />
          <span className="muted small">
            Case #{item.id} · decided by {item.decided_by_name} {item.decided_at ? timeAgo(item.decided_at) : ""}
          </span>
        </div>
        <p className="case-reason">Flagged: {item.reason}</p>
        {item.note && <p className="small">Moderator's note: {item.note}</p>}
        <p className="muted small">
          <Link to={`/listings/${item.listing_id}`}>{item.listing_title}</Link> · {shortName(item.advertiser_name)}
        </p>
      </div>
    </article>
  );
}
