import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, isSignedIn, signIn as apiSignIn, signOut as apiSignOut } from "./api";
import type { Me } from "./types";

type AuthState = {
  me: Me | null;
  signIn: (userId: number) => Promise<Me>;
  signOut: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);

  const refresh = useCallback(async () => {
    if (!isSignedIn()) return setMe(null);
    try {
      setMe(await api.me());
    } catch {
      apiSignOut();
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value: AuthState = {
    me,
    refresh,
    signIn: async (userId) => {
      const user = await apiSignIn(userId);
      setMe(user);
      return user;
    },
    signOut: () => {
      apiSignOut();
      setMe(null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
