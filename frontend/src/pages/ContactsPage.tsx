import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { Empty, NeedsRole, Stat, timeAgo } from "../components/ui";
import type { UnlockedListing } from "../types";

// A seeker's unlocked listings. Opening one again shows the contact for free.
export function ContactsPage() {
  const { me } = useAuth();
  const [unlocks, setUnlocks] = useState<UnlockedListing[] | null>(null);

  useEffect(() => {
    if (me?.role === "seeker") api.myUnlocks().then(setUnlocks).catch(() => setUnlocks([]));
  }, [me]);

  if (me?.role !== "seeker") return <NeedsRole who="home seekers" what="My contacts" />;

  return (
    <>
      <section className="page-head">
        <div>
          <h1>My contacts</h1>
          <p className="muted">Homes you unlocked. Opening one again is always free.</p>
        </div>
      </section>

      <div className="stats">
        <Stat label="Credits left" value={me.balance ?? 0} hint="bonus credits are spent first" />
        <Stat label="Contacts unlocked" value={unlocks?.length ?? "–"} />
      </div>

      <section className="panel">
        {unlocks?.length === 0 ? (
          <Empty title="Nothing unlocked yet">
            <Link to="/">Browse homes</Link> and unlock a contact for 1 credit.
          </Empty>
        ) : (
          <ul className="leads">
            {unlocks?.map((u) => (
              <li key={u.listing_id}>
                <span className="dot" aria-hidden />
                <Link to={`/listings/${u.listing_id}`}>{u.title}</Link>
                <span className="muted small">{timeAgo(u.unlocked_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
