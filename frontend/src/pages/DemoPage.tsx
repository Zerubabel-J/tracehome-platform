import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { Avatar, RoleBadge } from "../components/ui";
import { PERSONA_ORDER, PERSONAS, personaOf, shortName, type Persona } from "../roles";
import type { DemoUserOption } from "../types";

// The presenter's starting point: every made-up user, grouped by who they are, one click to sign in.
export function DemoPage() {
  const { me, signIn } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState<DemoUserOption[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    api
      .demoUsers()
      .then(setUsers)
      .catch(() => setError("Could not load the demo users. Is the API running?"));
  }, [me]); // reload after sign-in, so balances stay current

  async function choose(user: DemoUserOption) {
    setBusy(user.id);
    try {
      const signedIn = await signIn(user.id);
      navigate(PERSONAS[personaOf(signedIn)].home);
    } finally {
      setBusy(null);
    }
  }

  // Three groups, matching the three roles the API knows. Advertisers are sorted agency, agent,
  // broker, owner, so the four kinds sit side by side.
  const sections: { title: string; summary: string; users: DemoUserOption[] }[] = [
    {
      title: "Home seekers",
      summary: PERSONAS.seeker.summary,
      users: (users ?? []).filter((u) => u.role === "seeker"),
    },
    {
      title: "Advertisers",
      summary: "Owners, brokers and agencies (with their agents) publish homes and receive leads. They share one workspace.",
      users: (users ?? [])
        .filter((u) => u.role === "advertiser")
        .sort((a, b) => PERSONA_ORDER.indexOf(personaOf(a)) - PERSONA_ORDER.indexOf(personaOf(b))),
    },
    {
      title: "TraceHome staff",
      summary: PERSONAS.moderator.summary,
      users: (users ?? []).filter((u) => u.role === "moderator"),
    },
  ];

  return (
    <>
      <section className="hero small">
        <h1>Try TraceHome as anyone</h1>
        <p>
          Pick a made-up person to see the app the way they do. Sign-in tokens last 5 minutes and renew
          automatically; the real system will use Amazon Cognito.
        </p>
      </section>

      <ol className="script">
        <li>
          <strong>Seeker</strong> Hana unlocks a listing for 1 credit
        </li>
        <li>
          <strong>Advertiser</strong> sees Hana's lead appear at once
        </li>
        <li>
          <strong>Advertiser</strong> uploads a photo; the checks flag it
        </li>
        <li>
          <strong>Moderator</strong> Sara approves or rejects it
        </li>
      </ol>

      {error && <p className="alert error">{error}</p>}
      {!users && !error && <p className="muted">Loading demo users…</p>}

      {sections
        .filter((section) => section.users.length > 0)
        .map((section) => (
          <section key={section.title} className="persona-group">
            <div className="persona-head">
              <h2>{section.title}</h2>
              <p className="muted">{section.summary}</p>
            </div>
            <div className="people">
              {section.users.map((user) => (
                <PersonCard key={user.id} user={user} current={me?.id === user.id} busy={busy} onChoose={choose} />
              ))}
            </div>
          </section>
        ))}
    </>
  );
}

function PersonCard({
  user,
  current,
  busy,
  onChoose,
}: {
  user: DemoUserOption;
  current: boolean;
  busy: number | null;
  onChoose: (user: DemoUserOption) => Promise<void>;
}) {
  const persona: Persona = personaOf(user);
  return (
    <article className={`person ${current ? "current" : ""}`}>
      <div className="person-top">
        <Avatar name={user.display_name} persona={persona} size={44} />
        <div>
          <strong>{user.display_name}</strong>
          <div className="person-meta">
            <RoleBadge persona={persona} />
            {persona === "agent" && user.advertiser_name && (
              <span className="muted">at {shortName(user.advertiser_name)}</span>
            )}
            {user.role === "seeker" && <span className="muted">{user.hint.replace("seeker, ", "")}</span>}
          </div>
        </div>
      </div>
      <ul className="try">
        {PERSONAS[persona].tryThis.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      <button className={`btn block ${current ? "" : "ghost"}`} disabled={busy !== null} onClick={() => void onChoose(user)}>
        {current ? "Signed in · open" : busy === user.id ? "Signing in…" : `Sign in as ${user.display_name}`}
      </button>
    </article>
  );
}
