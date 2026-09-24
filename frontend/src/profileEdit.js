export function profilePatchFromDraft(profile, draft) {
  const fullName = draft.full_name.trim();
  if (!fullName) throw new Error("Enter your full name.");

  const phone = draft.phone.trim() || null;
  const patch = {};
  if (fullName !== profile.full_name) patch.full_name = fullName;
  if (phone !== (profile.phone ?? null)) patch.phone = phone;
  return patch;
}

export function hasEmailChange(profile, draft) {
  return draft.email.trim().toLowerCase() !== profile.email.toLowerCase();
}
