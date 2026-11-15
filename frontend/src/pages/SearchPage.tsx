import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { api, ApiError } from "../api";
import { Empty } from "../components/ui";
import { price, PROPERTY_TYPES, SUB_CITIES } from "../format";
import type { ListingSummary, SearchPage as Page } from "../types";

const FIELDS = ["q", "sub_city", "purpose", "property_type", "min_price", "max_price", "min_bedrooms"];

export function SearchPage() {
  // The search lives in the address bar, so a search can be shared and the back button works.
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setError(null);
    setLoading(true);
    api
      .search(params)
      .then(setResult)
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setLoading(false));
  }, [params]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams();
    for (const name of FIELDS) {
      const value = String(form.get(name) ?? "").trim();
      if (value) next.set(name, value);
    }
    setParams(next);
  }

  const page = Number(params.get("page") ?? "1");
  const goTo = (n: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(n));
    setParams(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const lastPage = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;
  const filtered = FIELDS.some((f) => params.get(f));

  return (
    <>
      <section className="hero">
        <h1>Find your next home in Addis Ababa</h1>
        <p>Browse for free. Unlock an advertiser's phone and email for one credit, only when you're interested.</p>

        <form className="searchbar" onSubmit={submit} key={params.toString()}>
          <input
            name="q"
            className="search-input"
            placeholder="Try “furnished Bole” or “villa garden”"
            defaultValue={params.get("q") ?? ""}
            aria-label="Search words"
          />
          <button type="submit" className="btn">
            Search
          </button>
          <div className="filters">
            <select name="purpose" defaultValue={params.get("purpose") ?? ""} aria-label="Rent or buy">
              <option value="">Rent or buy</option>
              <option value="rent">For rent</option>
              <option value="sale">For sale</option>
            </select>
            <select name="sub_city" defaultValue={params.get("sub_city") ?? ""} aria-label="Sub-city">
              <option value="">Any sub-city</option>
              {SUB_CITIES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
            <select name="property_type" defaultValue={params.get("property_type") ?? ""} aria-label="Property type">
              <option value="">Any type</option>
              {PROPERTY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t[0]!.toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
            <input name="min_bedrooms" type="number" min="0" placeholder="Min beds" defaultValue={params.get("min_bedrooms") ?? ""} />
            <input name="min_price" type="number" min="0" placeholder="Min ETB" defaultValue={params.get("min_price") ?? ""} />
            <input name="max_price" type="number" min="0" placeholder="Max ETB" defaultValue={params.get("max_price") ?? ""} />
          </div>
        </form>
      </section>

      {error && <p className="alert error">{error}</p>}

      {result && (
        <>
          <div className="results-head">
            <h2>
              {result.total.toLocaleString()} {result.total === 1 ? "home" : "homes"}
              {filtered ? " match your search" : " available"}
            </h2>
            {filtered && (
              <button className="btn ghost small" onClick={() => setParams(new URLSearchParams())}>
                Clear filters
              </button>
            )}
          </div>

          {result.items.length === 0 ? (
            <Empty title="No homes match">Try fewer words, or widen the price range.</Empty>
          ) : (
            <ul className={`grid ${loading ? "dim" : ""}`}>
              {result.items.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </ul>
          )}

          {lastPage > 1 && (
            <div className="pager">
              <button className="btn ghost" disabled={page <= 1} onClick={() => goTo(page - 1)}>
                ← Previous
              </button>
              <span className="muted">
                Page {page} of {lastPage}
              </span>
              <button className="btn ghost" disabled={page >= lastPage} onClick={() => goTo(page + 1)}>
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}

function ListingCard({ listing }: { listing: ListingSummary }) {
  return (
    <li className="card">
      <Link to={`/listings/${listing.id}`}>
        <div className="card-media">
          {listing.cover_photo_url ? (
            <img src={listing.cover_photo_url} alt="" loading="lazy" />
          ) : (
            <div className="no-photo">No photo yet</div>
          )}
          <span className={`tag-purpose ${listing.purpose}`}>{listing.purpose === "rent" ? "For rent" : "For sale"}</span>
        </div>
        <div className="card-body">
          <span className="card-price">{price(listing)}</span>
          <strong className="card-title">{listing.title}</strong>
          <span className="muted small">
            {listing.neighborhood}, {listing.sub_city}
          </span>
          <div className="facts-inline">
            <span>{listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} bed`}</span>
            <span>{listing.area_m2} m²</span>
            <span className="cap">{listing.property_type}</span>
          </div>
        </div>
      </Link>
    </li>
  );
}
