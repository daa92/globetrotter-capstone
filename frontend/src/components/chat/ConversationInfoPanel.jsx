import { useRef, useState } from "react";
import { Crown, LogOut, Trash2, UserPlus, X } from "lucide-react";
import * as api from "../../api/client";
import { ApiError } from "../../api/client";
import UserAvatar from "../layout/UserAvatar";
import UserPicker from "./UserPicker";

export default function ConversationInfoPanel({ accessToken, currentUsername, conversation, onClose, onChanged, onDeleted }) {
  const [name, setName] = useState(conversation.name || "");
  const [error, setError] = useState(null);
  const [addingMembers, setAddingMembers] = useState(false);
  const [toAdd, setToAdd] = useState([]);
  const pictureInputRef = useRef(null);

  const isGroup = conversation.type === "group";
  const me = conversation.members.find((m) => m.username === currentUsername);
  const isAdmin = me?.role === "admin";
  const otherMember = !isGroup ? conversation.members.find((m) => m.username !== currentUsername) : null;

  const run = async (fn) => {
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong");
    }
  };

  const handleRename = () =>
    run(async () => {
      if (!name.trim() || name.trim() === conversation.name) return;
      const updated = await api.updateConversation(accessToken, conversation.id, { name: name.trim() });
      onChanged(updated);
    });

  const handlePictureChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    run(async () => {
      const updated = await api.uploadGroupPicture(accessToken, conversation.id, file);
      onChanged(updated);
    });
  };

  const handleAddMembers = () =>
    run(async () => {
      if (toAdd.length === 0) return;
      const updated = await api.addConversationMembers(accessToken, conversation.id, toAdd.map((u) => u.username));
      onChanged(updated);
      setToAdd([]);
      setAddingMembers(false);
    });

  const handleRemove = (username) =>
    run(async () => {
      const result = await api.removeConversationMember(accessToken, conversation.id, username);
      if (result.deleted) onDeleted();
      else onChanged(result);
    });

  const handlePromote = (username, role) =>
    run(async () => {
      const updated = await api.setConversationMemberRole(accessToken, conversation.id, username, role);
      onChanged(updated);
    });

  const handleLeave = () =>
    run(async () => {
      const result = await api.removeConversationMember(accessToken, conversation.id, currentUsername);
      onDeleted();
      return result;
    });

  const handleDeleteGroup = () =>
    run(async () => {
      await api.deleteConversation(accessToken, conversation.id);
      onDeleted();
    });

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm overflow-y-auto bg-white dark:bg-neutral-900 p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">{isGroup ? "Group info" : "Contact"}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-full p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800">
            <X size={18} />
          </button>
        </div>

        <div className="mt-4 flex flex-col items-center gap-2">
          {isGroup ? (
            <>
              <button
                onClick={() => isAdmin && pictureInputRef.current?.click()}
                className="relative"
                disabled={!isAdmin}
                aria-label="Change group picture"
              >
                <UserAvatar user={{ username: conversation.name, profile_picture_url: conversation.picture_url }} size={72} />
              </button>
              <input ref={pictureInputRef} type="file" accept="image/*" className="hidden" onChange={handlePictureChange} />
              {isAdmin ? (
                <div className="mt-2 flex w-full items-center gap-2">
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onBlur={handleRename}
                    className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-1.5 text-sm text-center font-semibold outline-none focus:border-teal-600"
                  />
                </div>
              ) : (
                <p className="text-base font-bold">{conversation.name}</p>
              )}
              <p className="text-xs text-neutral-400">{conversation.members.length} members</p>
            </>
          ) : (
            <>
              <UserAvatar user={otherMember} size={72} />
              <p className="text-base font-bold">{otherMember?.username}</p>
            </>
          )}
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        {isGroup && (
          <div className="mt-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-neutral-500">Members</h3>
              {isAdmin && (
                <button
                  onClick={() => setAddingMembers((v) => !v)}
                  className="flex items-center gap-1 text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline"
                >
                  <UserPlus size={13} /> Add
                </button>
              )}
            </div>

            {addingMembers && (
              <div className="mt-2 rounded-lg border border-neutral-200 dark:border-neutral-700 p-2">
                <UserPicker
                  accessToken={accessToken}
                  excludeUsernames={conversation.members.map((m) => m.username)}
                  selected={toAdd}
                  onToggle={(u) => setToAdd((prev) => (prev.some((s) => s.username === u.username) ? prev.filter((s) => s.username !== u.username) : [...prev, u]))}
                />
                <button
                  onClick={handleAddMembers}
                  className="mt-2 w-full rounded-full bg-teal-700 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                >
                  Add to group
                </button>
              </div>
            )}

            <ul className="mt-2 divide-y divide-neutral-100 dark:divide-neutral-800">
              {conversation.members.map((m) => (
                <li key={m.username} className="flex items-center gap-2 py-2">
                  <UserAvatar user={m} size={30} />
                  <span className="flex-1 truncate text-sm">
                    {m.username} {m.username === currentUsername && <span className="text-neutral-400">(you)</span>}
                  </span>
                  {m.role === "admin" && <Crown size={14} className="text-goldhour-500" aria-label="Admin" />}
                  {isAdmin && m.username !== currentUsername && (
                    <div className="flex items-center gap-2 text-xs">
                      <button
                        onClick={() => handlePromote(m.username, m.role === "admin" ? "member" : "admin")}
                        className="text-teal-700 dark:text-teal-400 hover:underline"
                      >
                        {m.role === "admin" ? "Demote" : "Promote"}
                      </button>
                      <button onClick={() => handleRemove(m.username)} className="text-red-600 hover:underline">
                        Remove
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 space-y-2">
          {isGroup ? (
            <>
              <button
                onClick={handleLeave}
                className="flex w-full items-center justify-center gap-2 rounded-full border border-neutral-300 dark:border-neutral-600 py-2 text-sm font-semibold hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <LogOut size={15} /> Leave group
              </button>
              {isAdmin && (
                <button
                  onClick={handleDeleteGroup}
                  className="flex w-full items-center justify-center gap-2 rounded-full border border-red-300 dark:border-red-800 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                >
                  <Trash2 size={15} /> Delete group for everyone
                </button>
              )}
            </>
          ) : (
            <button
              onClick={handleDeleteGroup}
              className="flex w-full items-center justify-center gap-2 rounded-full border border-red-300 dark:border-red-800 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
            >
              <Trash2 size={15} /> Delete conversation
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
