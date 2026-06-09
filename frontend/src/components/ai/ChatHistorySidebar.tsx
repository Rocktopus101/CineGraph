"use client";

import { MessageSquarePlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatHistoryItem } from "@/lib/types";

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (sameDay) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

interface Props {
  items: ChatHistoryItem[];
  activeId: number | null;
  loading?: boolean;
  onSelect: (id: number) => void;
  onNewChat: () => void;
  onDelete: (id: number) => void;
}

export function ChatHistorySidebar({
  items,
  activeId,
  loading,
  onSelect,
  onNewChat,
  onDelete,
}: Props) {
  return (
    <aside className="flex w-full shrink-0 flex-col rounded-lg border border-border bg-card md:w-72">
      <div className="flex items-center justify-between border-b border-border p-3">
        <h2 className="text-sm font-semibold">Chat history</h2>
        <Button variant="ghost" size="sm" onClick={onNewChat} title="New chat">
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1 max-h-[calc(100vh-14rem)]">
        {loading && (
          <p className="px-2 py-4 text-center text-xs text-muted-foreground">Loading…</p>
        )}
        {!loading && items.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-muted-foreground">
            Past chats appear here after you send a message.
          </p>
        )}
        {items.map((item) => (
          <div
            key={item.id}
            className={`group flex items-start gap-1 rounded-md ${
              activeId === item.id ? "bg-primary/15" : "hover:bg-muted/60"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect(item.id)}
              className="min-w-0 flex-1 px-3 py-2 text-left"
            >
              <p className="truncate text-sm font-medium">{item.query_text}</p>
              {item.response_preview && (
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {item.response_preview}
                </p>
              )}
              <p className="mt-1 text-[10px] text-muted-foreground">{formatWhen(item.created_at)}</p>
            </button>
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 shrink-0 opacity-0 group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(item.id);
              }}
              title="Delete chat"
            >
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </div>
        ))}
      </div>
    </aside>
  );
}
