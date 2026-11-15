import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { api, ApiError, uploadToS3 } from "../api";
import { useAuth } from "../auth";
import { Avatar, Empty, NeedsRole, RoleBadge, Stat, StatusPill, timeAgo } from "../components/ui";
import { personaOf, shortName } from "../roles";
import type { AdvertiserListing, Lead } from "../types";

// Only approved photos have a public address; the others are shown as a labelled placeholder.
const HIDDEN_LABEL: Record<string, string> = {
  checking: "Being checked…",
  under_review: "Hidden until a moderator decides",
  rejected: "Not published",
  approved: "",
};

// One workspace for owners, brokers, agencies and their agents: they all publish listings,
// receive leads and add photos. The kind only changes the label.
export function WorkspacePage() {
  const { me } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [listings, setListings] = useState<AdvertiserListing[]>([]);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(async () => {
    const [newLeads, newListings] = await Promise.all([api.leads(), api.myListings()]);
    setLeads(newLeads);
    setListings(newListings);
  }, []);

  useEffect(() => {
    if (me?.role === "advertiser") void load();
  }, [me, load]);

  // While any photo is still being checked, ask for its status every 3 seconds.
  const checking = listings.some((l) => l.photos.some((p) => p.status === "checking"));
  useEffect(() => {
    if (!checking) return;
    const timer = setInterval(() => void load(), 3000);
    return () => clearInterval(timer);
  }, [checking, load]);

  async function upload(listingId: number, file: File | undefined) {
    if (!file) return;
    setMessage(null);
    setUploading(listingId);
    try {
      const ticket = await api.requestUpload(listingId, file); // 1. ask the API for a presigned POST
      await uploadToS3(ticket, file); // 2. upload straight to the private incoming bucket
      setMessage({ kind: "ok", text: "Uploaded. The automatic checks decide next; the status below updates by itself." });
      await load();
    } catch (e) {
      setMessage({ kind: "error", text: (e as ApiError).message });
    } finally {
      setUploading(null);
    }
  }

  if (me?.role !== "advertiser") {
    return <NeedsRole who="owners, brokers, agencies and agents" what="Advertiser workspace" />;
  }

  const persona = personaOf(me);
  const live = listings.filter((l) => l.status === "approved").length;
  const allPhotos = listings.flatMap((l) => l.photos);
  const waiting = allPhotos.filter((p) => p.status === "checking" || p.status === "under_review").length;
  const weekAgo = Date.now() - 7 * 86400_000;
  const leadsThisWeek = leads.filter((l) => new Date(l.created_at).getTime() > weekAgo).length;
  // Listings with photo news first, so a flagged photo is easy to find during the demo.
  const sorted = [...listings].sort(
    (a, b) => Number(b.photos.some((p) => p.status !== "approved")) - Number(a.photos.some((p) => p.status !== "approved")),
  );
  const shown = showAll ? sorted : sorted.slice(0, 6);

  return (
    <>
      <section className="page-head">
        <Avatar name={me.display_name} persona={persona} size={56} />
        <div>
          <h1>{shortName(me.advertiser_name ?? me.display_name)}</h1>
          <p className="muted">
            <RoleBadge persona={persona} />{" "}
            {persona === "agent"
              ? `Signed in as ${me.display_name}, sharing this agency's listings and leads`
              : "Your listings, leads and photos"}
          </p>
        </div>
      </section>

      <div className="stats">
        <Stat label="Live listings" value={live} hint={`${listings.length} in total`} />
        <Stat label="Leads" value={leads.length} hint={`${leadsThisWeek} this week`} />
        <Stat label="Photos waiting" value={waiting} hint="being checked or with a moderator" />
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Leads</h2>
          <span className="muted small">A seeker becomes a lead the moment they unlock your contact.</span>
        </div>
        {leads.length === 0 ? (
          <Empty title="No leads yet">Sign in as a seeker (from Demo users) and unlock one of your listings.</Empty>
        ) : (
          <ul className="leads">
            {leads.map((lead) => (
              <li key={lead.id}>
                <Avatar name={lead.seeker_name} persona="seeker" size={32} />
                <div>
                  <strong>{lead.seeker_name}</strong> unlocked{" "}
                  <Link to={`/listings/${lead.listing_id}`}>{lead.listing_title}</Link>
                </div>
                <span className="muted small" title={new Date(lead.created_at).toLocaleString()}>
                  {timeAgo(lead.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Listings and photos</h2>
          <span className="muted small">JPEG, PNG or WebP, up to 5 MB. Only approved photos are ever shown to the public.</span>
        </div>
        {message && <p className={`alert ${message.kind}`}>{message.text}</p>}
        <ul className="my-listings">
          {shown.map((listing) => (
            <li key={listing.id}>
              <div className="ml-head">
                <div>
                  <Link to={`/listings/${listing.id}`} className="ml-title">
                    {listing.title}
                  </Link>
                  <div className="muted small">
                    {listing.sub_city} · {listing.price_etb.toLocaleString()} ETB
                  </div>
                </div>
                <StatusPill status={listing.status} />
                <label className={`btn ghost small ${listing.status === "removed" ? "disabled" : ""}`}>
                  {uploading === listing.id ? "Uploading…" : "+ Add photo"}
                  <input
                    type="file"
                    hidden
                    disabled={listing.status === "removed" || uploading !== null}
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => {
                      void upload(listing.id, e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>
              {listing.photos.length > 0 && (
                <div className="thumbs">
                  {listing.photos.map((photo) => (
                    <figure key={photo.id} className={`photo-status s-${photo.status}`}>
                      {photo.url ? <img src={photo.url} alt="" /> : <div className="no-photo">{HIDDEN_LABEL[photo.status]}</div>}
                      <figcaption>
                        <StatusPill status={photo.status} />
                        {photo.reason && <small>{photo.reason}</small>}
                      </figcaption>
                    </figure>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
        {sorted.length > 6 && (
          <button className="btn ghost block" onClick={() => setShowAll(!showAll)}>
            {showAll ? "Show fewer" : `Show all ${sorted.length} listings`}
          </button>
        )}
      </section>
    </>
  );
}
