import { useState } from "react";

/**
 * Shows the user's profile picture if they have one and it loads
 * correctly; otherwise falls back to a colored circle with their first
 * initial — same "never show a broken image" pattern as DestinationImage.
 */
export default function UserAvatar({ user, size = 28 }) {
  const [failed, setFailed] = useState(false);
  const hasPhoto = user?.profile_picture_url && !failed;
  const initial = (user?.username || "?").charAt(0).toUpperCase();

  if (hasPhoto) {
    return (
      <img
        src={user.profile_picture_url}
        alt={user.username}
        onError={() => setFailed(true)}
        style={{ width: size, height: size }}
        className="rounded-full object-cover border border-neutral-300 dark:border-neutral-600"
      />
    );
  }

  return (
    <div
      style={{ width: size, height: size, backgroundColor: "#127C71" }}
      className="flex items-center justify-center rounded-full text-xs font-semibold text-white shrink-0"
    >
      {initial}
    </div>
  );
}
