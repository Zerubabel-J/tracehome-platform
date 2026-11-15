import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { price } from "../format";
import { shortName, type Persona } from "../roles";
import { RoleBadge } from "../components/ui";
import type { ListingDetail, UnlockResult } from "../types";

export function ListingPage() {
  const id = Number(useParams().id);
  const { me, refresh } = useAuth();
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [unlocked, setUnlocked] = useState<UnlockResult | null>(null);
  const [alreadyUnlocked, setAlreadyUnlocked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState(0);
  // One ID per unlock attempt. If the request fails on the network and the seeker taps again,
  // the same ID is sent, so the server can't charge twice. It is replaced after a clear answer.
  const attemptId = useRef(crypto.randomUUID());

  useEffect(() => {
    setUnlocked(null);
    setPhoto(0);
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

  if (error && !listing) {
    return (
      <div className="gate">
        <h1>Listing not available</h1>
        <p>{error}</p>
        <Link to="/" className="btn">
          Back to search
        </Link>
      </div>
    );
  }
  if (!listing) return <p className="muted">Loading…</p>;

  const photos = listing.photo_urls;
  const facts: [string, string][] = [
    ["Price", price(listing)],
    ["Type", listing.property_type[0]!.toUpperCase() + listing.property_type.slice(1)],
    ["Bedrooms", listing.bedrooms === 0 ? "Studio" : String(listing.bedrooms)],
    ["Area", `${listing.area_m2} m²`],
    ["Sub-city", listing.sub_city],
    ["Neighbourhood", listing.neighborhood],
  ];

  return (
    <>
      <Link to="/" className="back">
        ← Back to search
      </Link>

      <div className="listing-layout">
        <article>
          <div className="gallery">
            {photos.length === 0 ? (
              <div className="no-photo big">No approved photos yet</div>
            ) : (
              <img src={photos[photo]} alt={`Photo ${photo + 1} of ${listing.title}`} />
            )}
            <span className={`tag-purpose ${listing.purpose}`}>{listing.purpose === "rent" ? "For rent" : "For sale"}</span>
          </div>
          {photos.length > 1 && (
            <div className="thumb-row">
              {photos.map((url, i) => (
                <button key={url} className={`thumb ${i === photo ? "active" : ""}`} onClick={() => setPhoto(i)}>
                  <img src={url} alt={`Photo ${i + 1}`} />
                </button>
              ))}
            </div>
          )}

          <h1 className="listing-title">{listing.title}</h1>
          <p className="muted">
            {listing.neighborhood}, {listing.sub_city} · listed {new Date(listing.created_at).toLocaleDateString()}
          </p>

          <dl className="facts">
            {facts.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <h2>About this home</h2>
          <p className="description">{listing.description}</p>
        </article>

        <aside className="contact-card">
          <span className="card-price big">{price(listing)}</span>
          <div className="advertiser-line">
            <span className="muted">Advertised by</span>
            <strong>{shortName(listing.advertiser_name)}</strong>
            <RoleBadge persona={listing.advertiser_kind as Persona} />
          </div>

          {unlocked ? (
            <div className="contact revealed">
              <span className="eyebrow">Contact details</span>
              <a href={`tel:${unlocked.contact.phone.replace(/\s/g, "")}`}>{unlocked.contact.phone}</a>
              <a href={`mailto:${unlocked.contact.email}`}>{unlocked.contact.email}</a>
              <p className="alert ok">
                {unlocked.charged
                  ? `1 credit spent · ${unlocked.balance} left`
                  : "Already unlocked before, so nothing was spent"}
              </p>
            </div>
          ) : me?.role === "seeker" ? (
            <>
              <div className="contact hidden-contact">
                <span className="eyebrow">Contact details</span>
                <span className="blur">+251 ••• ••• •••</span>
                <span className="blur">••••••@example.com</span>
              </div>
              <button className="btn block big" onClick={unlock} disabled={busy}>
                {busy ? "Unlocking…" : alreadyUnlocked ? "Show contact (free, already unlocked)" : "Unlock contact · 1 credit"}
              </button>
              <p className="muted small">The advertiser sees you as a lead. You're never charged twice for the same home.</p>
              {error && <p className="alert error">{error}</p>}
            </>
          ) : (
            <div className="contact hidden-contact">
              <span className="eyebrow">Contact details</span>
              <span className="blur">+251 ••• ••• •••</span>
              <p className="muted small">
                {me ? "Only seekers can unlock contacts." : "Sign in as a seeker to unlock the contact for 1 credit."}
              </p>
              {!me && (
                <Link to="/demo" className="btn block">
                  Choose a demo seeker
                </Link>
              )}
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
