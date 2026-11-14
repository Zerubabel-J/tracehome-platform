import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { api, ApiError, uploadToS3 } from "../api";
import { useAuth } from "../auth";
import type { AdvertiserListing, Lead } from "../types";

const STATUS_LABEL = {
  checking: "Checking…",
  approved: "Approved",
  under_review: "Under review",
  rejected: "Rejected",
};

export function AdvertiserPage() {
  const { me } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [listings, setListings] = useState<AdvertiserListing[]>([]);
  const [message, setMessage] = useState<string | null>(null);

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
    try {
      const ticket = await api.requestUpload(listingId, file); // 1. ask the API for a presigned POST
      await uploadToS3(ticket, file); // 2. upload straight to the incoming bucket
      setMessage(
        "Uploaded. S3 has the file, but it is not approved yet. Locally, play the checks with: " +
          "docker compose exec worker python scripts/simulate_check_result.py",
      );
      await load();
    } catch (e) {
      setMessage((e as ApiError).message);
    }
  }

  if (me?.role !== "advertiser") {
    return <p className="muted">Sign in as a demo advertiser to see the workspace.</p>;
  }

  return (
    <>
      <h1>{me.advertiser_name}</h1>

      <section>
        <h2>Leads ({leads.length})</h2>
        <p className="muted">Every unlock creates a lead here, in the same transaction.</p>
        {leads.length === 0 ? (
          <p className="muted">No leads yet. Sign in as a seeker and unlock one of your listings.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Seeker</th>
                <th>Listing</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>{new Date(lead.created_at).toLocaleString()}</td>
                  <td>{lead.seeker_name}</td>
                  <td>
                    <Link to={`/listings/${lead.listing_id}`}>{lead.listing_title}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>My listings and photos</h2>
        {message && <p className="notice">{message}</p>}
        <ul className="my-listings">
          {listings.map((listing) => (
            <li key={listing.id}>
              <div className="row">
                <strong>{listing.title}</strong>
                <span className="muted">
                  {listing.sub_city} · {listing.status}
                </span>
                <label className="upload">
                  Add photo
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => {
                      void upload(listing.id, e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>
              <div className="thumbs">
                {listing.photos.map((photo) => (
                  <figure key={photo.id} className={`photo-status ${photo.status}`}>
                    {photo.url ? <img src={photo.url} alt="" /> : <div className="no-photo">#{photo.id}</div>}
                    <figcaption>
                      {STATUS_LABEL[photo.status]}
                      {photo.reason && <small>{photo.reason}</small>}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
