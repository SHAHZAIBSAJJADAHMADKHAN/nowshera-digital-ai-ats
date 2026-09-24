export const isSameResolvedUser=(resolvedUserId,session)=>Boolean(resolvedUserId&&session?.user?.id===resolvedUserId);
