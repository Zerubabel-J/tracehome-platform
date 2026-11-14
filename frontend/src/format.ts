import type { ListingSummary } from "./types";

export const SUB_CITIES = [
  "Addis Ketema",
  "Akaky Kaliti",
  "Arada",
  "Bole",
  "Gullele",
  "Kirkos",
  "Kolfe Keranio",
  "Lemi Kura",
  "Lideta",
  "Nifas Silk-Lafto",
  "Yeka",
];

export const PROPERTY_TYPES = ["apartment", "condominium", "house", "villa", "studio"];

export function price(listing: Pick<ListingSummary, "price_etb" | "purpose">): string {
  const amount = new Intl.NumberFormat("en-US").format(listing.price_etb);
  return listing.purpose === "rent" ? `${amount} ETB / month` : `${amount} ETB`;
}

export function rooms(listing: Pick<ListingSummary, "bedrooms" | "area_m2">): string {
  const beds = listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} bed`;
  return `${beds} · ${listing.area_m2} m²`;
}
