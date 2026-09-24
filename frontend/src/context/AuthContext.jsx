import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import { supabase } from "../lib/supabase";
import { isSameResolvedUser } from "../authSync";

const C = createContext(null);
export const useAuth = () => useContext(C);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const timer = useRef(null);
  const resolvedUserId = useRef(null);

  const resolve = async s => {
    const id = ++seq.current;
    if (!s) {
      resolvedUserId.current = null;
      setSession(null);
      setProfile(null);
      setLoading(false);
      return null;
    }
    const sameUser = isSameResolvedUser(resolvedUserId.current, s);
    setSession(s);
    if (!sameUser) {
      resolvedUserId.current = null;
      setLoading(true);
      setProfile(null);
    }
    try {
      let nextProfile;
      try {
        nextProfile = await api("/auth/me", { token: s.access_token });
      } catch (error) {
        if (error.status !== 403) throw error;
        await api("/candidate/profile/bootstrap", { token: s.access_token, method: "POST" });
        nextProfile = await api("/auth/me", { token: s.access_token });
      }
      if (id === seq.current) {
        resolvedUserId.current = s.user.id;
        setProfile(nextProfile);
        setLoading(false);
      }
      return nextProfile;
    } catch (error) {
      if (id === seq.current) {
        resolvedUserId.current = null;
        setSession(null);
        setProfile(null);
        setLoading(false);
      }
      throw error;
    }
  };

  const deferResolve = s => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      timer.current = null;
      resolve(s).catch(() => {});
    }, 0);
  };

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => resolve(data.session)).catch(() => resolve(null));
    const { data: listener } = supabase.auth.onAuthStateChange((_, s) => {
      deferResolve(s);
    });
    return () => {
      if (timer.current) clearTimeout(timer.current);
      listener.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo(() => ({
    session,
    token: session?.access_token ?? null,
    profile,
    loading,
    signIn: async (email, password) => {
      const result = await supabase.auth.signInWithPassword({ email, password });
      if (!result.error && result.data.session) {
        resolvedUserId.current = null;
        setSession(result.data.session);
        setProfile(null);
        setLoading(true);
        deferResolve(result.data.session);
      }
      return result;
    },
    signUp: ({ email, password, fullName }) => supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    }),
    refreshProfile: () => (session ? resolve(session) : Promise.resolve(null)),
    updatePassword: password => supabase.auth.updateUser({ password }),
    signOut: async () => {
      setLoading(true);
      try {
        return await supabase.auth.signOut();
      } finally {
        await resolve(null);
      }
    },
  }), [session, profile, loading]);

  return <C.Provider value={value}>{children}</C.Provider>;
}
