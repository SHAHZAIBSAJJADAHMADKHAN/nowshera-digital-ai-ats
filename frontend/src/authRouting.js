export function roleRouteState({ loading, session, profile }, requiredRole) {
  if (loading || (session && !profile)) return { type: "loading" };
  if (profile?.role === requiredRole) return { type: "allow" };
  return { type: "redirect", to: profile?.role ? `/${profile.role}` : "/access-denied" };
}

export function protectedRouteState({ loading, session }) {
  if (loading) return { type: "loading" };
  return session ? { type: "allow" } : { type: "redirect", to: "/login" };
}
