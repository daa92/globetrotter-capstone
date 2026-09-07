/**
 * A direct conversation has no name/picture of its own — it borrows the
 * other participant's. A group has its own name/picture. Centralised
 * here so the conversation list, chat header, and info panel all agree.
 */
export function conversationDisplay(conversation, currentUsername) {
  if (conversation.type === "group") {
    return {
      name: conversation.name || "Group",
      avatarUser: { username: conversation.name || "G", profile_picture_url: conversation.picture_url },
      subtitle: `${conversation.members.length} members`,
    };
  }
  const other = conversation.members.find((m) => m.username !== currentUsername) || conversation.members[0];
  return {
    name: other?.username || "Unknown",
    avatarUser: other,
    subtitle: null,
  };
}

export function messagePreview(message) {
  if (!message) return "No messages yet";
  if (message.deleted) return "Message deleted";
  if (message.type === "text") return message.text || "";
  const labels = { image: "📷 Photo", video: "🎬 Video", audio: "🎵 Audio", file: "📎 File" };
  const label = labels[message.type] || "Attachment";
  return message.text ? `${label} · ${message.text}` : label;
}
