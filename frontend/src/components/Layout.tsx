import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import type { DemoUser } from "../types";

export function Layout() {
  const { me, signIn, signOut } = useAuth();
  const [users, setUsers] = useState<DemoUser[]>([]);

  useEffect(() => {
    api.demoUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          TraceHome <span className="tag">demo · made-up data</span>
        </Link>
        <nav>
          <Link to="/">Search</Link>
          {me?.role === "advertiser" && <Link to="/advertiser">My workspace</Link>}
        </nav>
        <div className="account">
          {me ? (
            <>
              <span>
                {me.display_name}
                {me.balance !== null && <strong className="balance"> · {me.balance} credits</strong>}
              </span>
              <button className="link" onClick={signOut}>
                Sign out
              </button>
            </>
          ) : (
            <label>
              Demo sign-in{" "}
              <select defaultValue="" onChange={(e) => e.target.value && signIn(Number(e.target.value))}>
                <option value="" disabled>
                  Choose a made-up user…
                </option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
