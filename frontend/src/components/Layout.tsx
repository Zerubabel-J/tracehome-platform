import { NavLink, Outlet, useNavigate } from "react-router";
import { useAuth } from "../auth";
import { personaOf } from "../roles";
import { Avatar, RoleBadge } from "./ui";

export function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path d="M8 16 L16 9 L24 16 V24 H19 V19 H13 V24 H8 Z" fill="#fff" />
    </svg>
  );
}

export function Layout() {
  const { me, signOut } = useAuth();
  const navigate = useNavigate();
  const persona = me ? personaOf(me) : null;

  return (
    <div className="shell">
      <div className="demo-strip">Demo for Group 9 · every person, listing and phone number here is made up</div>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <Logo />
            <span>TraceHome</span>
          </NavLink>

          <nav className="nav">
            <NavLink to="/" end>
              Browse homes
            </NavLink>
            {me?.role === "seeker" && <NavLink to="/contacts">My contacts</NavLink>}
            {me?.role === "advertiser" && <NavLink to="/workspace">Workspace</NavLink>}
            {me?.role === "moderator" && <NavLink to="/moderation">Moderation</NavLink>}
            <NavLink to="/demo">Demo users</NavLink>
          </nav>

          <div className="account">
            {me && persona ? (
              <>
                {me.balance !== null && (
                  <span className="credits" title="Usable credits">
                    {me.balance} {me.balance === 1 ? "credit" : "credits"}
                  </span>
                )}
                <div className="me">
                  <Avatar name={me.display_name} persona={persona} size={34} />
                  <div className="me-text">
                    <strong>{me.display_name}</strong>
                    <RoleBadge persona={persona} />
                  </div>
                </div>
                <button
                  className="btn ghost small"
                  onClick={() => {
                    signOut();
                    navigate("/demo");
                  }}
                >
                  Switch user
                </button>
              </>
            ) : (
              <NavLink to="/demo" className="btn">
                Sign in as a demo user
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main className="page">
        <Outlet />
      </main>

      <footer className="footer">
        TraceHome · a property platform for Addis Ababa · Evangadi AWS course, Group 9 · made-up data only
      </footer>
    </div>
  );
}
