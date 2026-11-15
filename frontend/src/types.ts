// Shapes of the API's responses (see http://localhost:8080/api/docs).

export type ListingSummary = {
  id: number;
  title: string;
  purpose: "rent" | "sale";
  property_type: string;
  sub_city: string;
  neighborhood: string;
  price_etb: number;
  bedrooms: number;
  area_m2: number;
  cover_photo_url: string | null;
};

export type ListingDetail = ListingSummary & {
  description: string;
  advertiser_name: string;
  advertiser_kind: string;
  photo_urls: string[];
  created_at: string;
};

export type SearchPage = {
  items: ListingSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type Role = "seeker" | "advertiser" | "moderator";
export type AdvertiserKind = "owner" | "broker" | "agency";

export type DemoUser = {
  id: number;
  display_name: string;
  role: Role;
  advertiser_name: string | null;
  advertiser_kind: AdvertiserKind | null;
};

export type DemoUserOption = DemoUser & { hint: string };

export type Me = DemoUser & { balance: number | null };

export type UnlockResult = {
  unlock_id: number;
  listing_id: number;
  outcome: "unlocked" | "already_unlocked" | "replayed";
  charged: boolean;
  balance: number;
  contact: { advertiser_name: string; phone: string; email: string };
};

export type UnlockedListing = { listing_id: number; title: string; unlocked_at: string };

export type Lead = {
  id: number;
  listing_id: number;
  listing_title: string;
  seeker_name: string;
  created_at: string;
};

export type PhotoStatus = {
  id: number;
  status: "checking" | "approved" | "under_review" | "rejected";
  reason: string | null;
  url: string | null;
  created_at: string;
};

export type AdvertiserListing = {
  id: number;
  title: string;
  status: string;
  sub_city: string;
  price_etb: number;
  photos: PhotoStatus[];
};

export type UploadTicket = {
  photo_id: number;
  status: string;
  upload: { url: string; fields: Record<string, string> };
  expires_in: number;
};

export type ReviewCase = {
  id: number;
  status: "open" | "closed";
  reason: string;
  created_at: string;
  photo_id: number;
  listing_id: number;
  listing_title: string;
  advertiser_name: string;
  advertiser_kind: AdvertiserKind;
  preview_url: string | null;
  decision: "approved" | "rejected" | null;
  decided_by_name: string | null;
  decided_at: string | null;
  note: string | null;
};

export type ModerationSummary = { open: number; approved: number; rejected: number };
