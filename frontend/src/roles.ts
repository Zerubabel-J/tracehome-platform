// Who is who in the demo. The API knows three roles (seeker, advertiser, moderator); advertisers
// are owners, brokers, or agencies, and an agency can have agents who sign in to its workspace.
import type { DemoUser } from "./types";

export type Persona = "seeker" | "owner" | "broker" | "agency" | "agent" | "moderator";

export const PERSONAS: Record<
  Persona,
  { label: string; plural: string; home: string; summary: string; tryThis: string[] }
> = {
  seeker: {
    label: "Seeker",
    plural: "Home seekers",
    home: "/",
    summary: "Looking for a place to rent or buy. Browses for free and spends 1 credit to see a contact.",
    tryThis: ["Search for “furnished Bole”", "Open a listing and unlock the contact", "See it under My contacts"],
  },
  agency: {
    label: "Agency",
    plural: "Agencies",
    home: "/workspace",
    summary: "A real-estate company with many listings and several people working for it.",
    tryThis: ["See which seekers unlocked your listings", "Upload a photo and watch its check status"],
  },
  agent: {
    label: "Agent",
    plural: "Agents",
    home: "/workspace",
    summary: "Works for an agency and shares its listings and leads.",
    tryThis: ["Open the agency workspace", "Follow up the newest lead"],
  },
  broker: {
    label: "Broker",
    plural: "Brokers",
    home: "/workspace",
    summary: "An independent broker advertising homes for their clients.",
    tryThis: ["Check your leads", "See a flagged photo waiting for a moderator"],
  },
  owner: {
    label: "Owner",
    plural: "Owners",
    home: "/workspace",
    summary: "Owns the home and advertises it directly.",
    tryThis: ["See who unlocked your listing", "Add a photo to a listing"],
  },
  moderator: {
    label: "Moderator",
    plural: "Moderators",
    home: "/moderation",
    summary: "Decides the doubtful cases that the automatic checks send to a person.",
    tryThis: ["Open a flagged photo", "Approve or reject it, with a reason", "See the decision history"],
  },
};

export const PERSONA_ORDER: Persona[] = ["seeker", "agency", "agent", "broker", "owner", "moderator"];

export function personaOf(user: DemoUser): Persona {
  if (user.role === "seeker") return "seeker";
  if (user.role === "moderator") return "moderator";
  if (user.advertiser_kind === "agency") {
    // The agency's own account carries the agency's name; anyone else on it is an agent.
    return user.advertiser_name?.endsWith(user.display_name) ? "agency" : "agent";
  }
  return user.advertiser_kind ?? "owner";
}

export function initials(name: string): string {
  return name
    .replace(/\(.*\)/, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join("");
}

/** "Demo Agency: Acacia Homes" → "Acacia Homes" */
export const shortName = (advertiserName: string) => advertiserName.replace(/^Demo [A-Za-z]+: /, "");
