import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { api, ApiError } from "../api";
import { price, PROPERTY_TYPES, rooms, SUB_CITIES } from "../format";
import type { SearchPage as Page } from "../types";

const FIELDS = ["q", "sub_city", "purpose", "property_type", "min_price", "max_price", "min_bedrooms"];

export function SearchPage() {
  // The search lives in the address bar, so a search can be shared and the back button works.
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .search(params)
      .then(setResult)
      .catch((e: ApiError) => setError(e.message));
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
  };
  const lastPage = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <>
      <form className="filters" onSubmit={submit} key={params.toString()}>
        <input name="q" placeholder="Search: e.g. furnished Bole, villa garden" defaultValue={params.get("q") ?? ""} />
        <select name="sub_city" defaultValue={params.get("sub_city") ?? ""}>
          <option value="">Any sub-city</option>
          {SUB_CITIES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select name="purpose" defaultValue={params.get("purpose") ?? ""}>
          <option value="">Rent or buy</option>
          <option value="rent">Rent</option>
          <option value="sale">Buy</option>
        </select>
        <select name="property_type" defaultValue={params.get("property_type") ?? ""}>
          <option value="">Any type</option>
          {PROPERTY_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <input name="min_price" type="number" min="0" placeholder="Min ETB" defaultValue={params.get("min_price") ?? ""} />
        <input name="max_price" type="number" min="0" placeholder="Max ETB" defaultValue={params.get("max_price") ?? ""} />
        <input name="min_bedrooms" type="number" min="0" placeholder="Min beds" defaultValue={params.get("min_bedrooms") ?? ""} />
        <button type="submit">Search</button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && (
        <>
          <p className="muted">{result.total} listings</p>
          <ul className="grid">
            {result.items.map((listing) => (
              <li key={listing.id} className="card">
                <Link to={`/listings/${listing.id}`}>
                  {listing.cover_photo_url ? (
                    <img src={listing.cover_photo_url} alt="" loading="lazy" />
                  ) : (
                    <div className="no-photo">No photo yet</div>
                  )}
                  <div className="card-body">
                    <strong>{listing.title}</strong>
                    <span>{price(listing)}</span>
                    <span className="muted">
                      {listing.neighborhood}, {listing.sub_city} · {rooms(listing)}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          {lastPage > 1 && (
            <div className="pager">
              <button disabled={page <= 1} onClick={() => goTo(page - 1)}>
                Previous
              </button>
              <span>
                Page {page} of {lastPage}
              </span>
              <button disabled={page >= lastPage} onClick={() => goTo(page + 1)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
