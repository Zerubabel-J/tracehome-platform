import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { price, rooms } from "../format";
import type { ListingDetail, UnlockResult } from "../types";

export function ListingPage() {
  const id = Number(useParams().id);
  const { me, refresh } = useAuth();
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [unlocked, setUnlocked] = useState<UnlockResult | null>(null);
  const [alreadyUnlocked, setAlreadyUnlocked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // One ID per unlock attempt. If the request fails on the network and the seeker taps again,
  // the same ID is sent, so the server can't charge twice. It is replaced after a clear answer.
  const attemptId = useRef(crypto.randomUUID());

  useEffect(() => {
    setUnlocked(null);
    api
      .listing(id)
      .then(setListing)
      .catch((e: ApiError) => setError(e.message));
  }, [id]);

  useEffect(() => {
    if (me?.role !== "seeker") return setAlreadyUnlocked(false);
    api
      .myUnlocks()
      .then((list) => setAlreadyUnlocked(list.some((u) => u.listing_id === id)))
      .catch(() => setAlreadyUnlocked(false));
  }, [me, id]);

  async function unlock() {
    setBusy(true);
    setError(null);
    try {
      setUnlocked(await api.unlock(id, attemptId.current));
      attemptId.current = crypto.randomUUID();
      await refresh(); // show the new balance
    } catch (e) {
      const apiError = e as ApiError;
      if (apiError.status) attemptId.current = crypto.randomUUID(); // a clear "no"
      setError(apiError.message || "Network problem. Try again: you won't be charged twice.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !listing) return <p className="error">{error}</p>;
  if (!listing) return <p className="muted">Loading…</p>;

  return (
    <article className="listing">
      <Link to="/" className="muted">
        ← Back to search
      </Link>
      <h1>{listing.title}</h1>
      <p className="price">{price(listing)}</p>
      <p className="muted">
        {listing.neighborhood}, {listing.sub_city} · {rooms(listing)} · {listing.property_type}
      </p>
      <div className="photos">
        {listing.photo_urls.length === 0 && <div className="no-photo">No approved photos yet</div>}
        {listing.photo_urls.map((url) => (
          <img key={url} src={url} alt="" />
        ))}
      </div>
      <p>{listing.description}</p>
      <p className="muted">
        Advertised by {listing.advertiser_name} ({listing.advertiser_kind})
      </p>

      <section className="unlock">
        <h2>Contact the advertiser</h2>
        {unlocked ? (
          <div className="contact">
            <p>
              <strong>{unlocked.contact.advertiser_name}</strong>
              <br />
              {unlocked.contact.phone} · {unlocked.contact.email}
            </p>
            <p className="muted">
              {unlocked.charged
                ? `1 credit spent. ${unlocked.balance} left.`
                : "You had already unlocked this listing, so nothing was spent."}
            </p>
          </div>
        ) : me?.role === "seeker" ? (
          <>
            <button onClick={unlock} disabled={busy}>
              {alreadyUnlocked ? "Show contact (already unlocked, free)" : "Unlock contact for 1 credit"}
            </button>
            {error && <p className="error">{error}</p>}
          </>
        ) : (
          <p className="muted">Sign in as a demo seeker to unlock the contact for 1 credit.</p>
        )}
      </section>
    </article>
  );
}
