"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function useSupabaseAuth() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();

    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsSignedIn(Boolean(session));
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsSignedIn(Boolean(session));
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  return { isSignedIn, loading };
}
