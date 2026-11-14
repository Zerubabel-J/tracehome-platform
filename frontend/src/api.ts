// Every call uses a relative path (/api/...). The website and the API share one address, so
// the same build works locally and behind CloudFront, with no CORS for API calls.
import type {
  AdvertiserListing,
  DemoUserOption,
  Lead,
  ListingDetail,
  Me,
  SearchPage,
  UnlockResult,
  UnlockedListing,
  UploadTicket,
} from "./types";

const TOKEN_KEY = "tracehome.token";
const USER_KEY = "tracehome.userId";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");

  const response = await fetch(path, { ...init, headers });

  // Demo tokens last 5 minutes (decision 82). Sign in again as the same demo user, once.
  const userId = sessionStorage.getItem(USER_KEY);
  if (response.status === 401 && retry && userId) {
    await signIn(Number(userId));
    return request<T>(path, init, false);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(
      response.status,
      detail?.code ?? "error",
      detail?.message ?? (typeof detail === "string" ? detail : response.statusText),
    );
  }
  return response.json() as Promise<T>;
}

export async function signIn(userId: number): Promise<Me> {
  const result = await request<{ token: string; user: Me }>(
    "/api/auth/demo-sign-in",
    { method: "POST", body: JSON.stringify({ user_id: userId }) },
    false,
  );
  sessionStorage.setItem(TOKEN_KEY, result.token);
  sessionStorage.setItem(USER_KEY, String(userId));
  return result.user;
}

export function signOut() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export const isSignedIn = () => sessionStorage.getItem(USER_KEY) !== null;

export const api = {
  demoUsers: () => request<DemoUserOption[]>("/api/auth/demo-users"),
  me: () => request<Me>("/api/me"),
  search: (params: URLSearchParams) => request<SearchPage>(`/api/listings?${params}`),
  listing: (id: number) => request<ListingDetail>(`/api/listings/${id}`),
  myUnlocks: () => request<UnlockedListing[]>("/api/me/unlocks"),
  // The idempotency key makes a retry safe: the server returns the first result, never a
  // second charge.
  unlock: (id: number, idempotencyKey: string) =>
    request<UnlockResult>(`/api/listings/${id}/unlock`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  leads: () => request<Lead[]>("/api/advertiser/leads"),
  myListings: () => request<AdvertiserListing[]>("/api/advertiser/listings"),
  requestUpload: (listingId: number, file: File) =>
    request<UploadTicket>(`/api/advertiser/listings/${listingId}/photo-uploads`, {
      method: "POST",
      body: JSON.stringify({ content_type: file.type, size_bytes: file.size }),
    }),
};

// Upload straight to S3 with the presigned POST. The API never handles the file.
export async function uploadToS3(ticket: UploadTicket, file: File): Promise<void> {
  const form = new FormData();
  for (const [name, value] of Object.entries(ticket.upload.fields)) form.append(name, value);
  form.append("file", file); // S3 requires the file to be the last field
  const response = await fetch(ticket.upload.url, { method: "POST", body: form });
  if (!response.ok) {
    throw new ApiError(response.status, "upload_failed", "S3 refused the upload (too big or wrong type?).");
  }
}
