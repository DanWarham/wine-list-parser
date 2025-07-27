'use client'
import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "./lib/supabaseClient";
import { Session, User } from "@supabase/supabase-js";
import { api } from "@/utils/api_v2";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  session: Session | null;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  session: null,
  signOut: async () => {},
});

async function syncUserWithBackend(user: User | null, session: Session | null) {
  if (!user || !session) return;
  try {
    await api.getCurrentUser(session.access_token);
  } catch (e) {
    console.error('Sync user error:', e);
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
      if (session?.user) {
        syncUserWithBackend(session.user, session);
      }
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
      if (session?.user) {
        await syncUserWithBackend(session.user, session);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const value = {
    user,
    loading,
    session,
    signOut: async () => {
      await supabase.auth.signOut();
      setUser(null);
      setSession(null);
    }
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}