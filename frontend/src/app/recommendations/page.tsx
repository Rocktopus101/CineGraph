"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { AIChatPanel, type ChatMessage } from "@/components/ai/AIChatPanel";
import { ChatHistorySidebar } from "@/components/ai/ChatHistorySidebar";
import { Button } from "@/components/ui/button";
import { isDevMode } from "@/lib/firebase";

export default function RecommendationsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, loading } = useAuth();
  const skipOnboarding = isDevMode && process.env.NEXT_PUBLIC_DEV_MODE === "true";

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeQueryId, setActiveQueryId] = useState<number | null>(null);

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ["chat-history"],
    queryFn: () => api.getChatHistory(),
    enabled: !!user,
  });

  useEffect(() => {
    if (!isDevMode && !loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  const refreshHistory = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["chat-history"] });
  }, [qc]);

  const loadHistoryItem = useCallback(async (id: number) => {
    const detail = await api.getChatHistoryDetail(id);
    setActiveQueryId(id);
    setMessages([
      { role: "user", content: detail.query_text },
      {
        role: "assistant",
        content: detail.response_text,
        citations: detail.citations,
        queryId: detail.id,
      },
    ]);
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setActiveQueryId(null);
  }, []);

  const handleDelete = useCallback(
    async (id: number) => {
      await api.deleteChatHistory(id);
      if (activeQueryId === id) {
        handleNewChat();
      }
      refreshHistory();
    },
    [activeQueryId, handleNewChat, refreshHistory],
  );

  if (!user?.has_completed_import && !skipOnboarding) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold mb-4">AI Recommendations</h1>
        <p className="text-muted-foreground mb-6">Import your Letterboxd data to get personalized recommendations.</p>
        <Link href="/onboarding/import"><Button>Import Data</Button></Link>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">AI Recommendations</h1>
        <p className="text-sm text-muted-foreground">
          Grounded in your viewing history. Chats are saved to your account.
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-4 md:flex-row">
        <ChatHistorySidebar
          items={history}
          activeId={activeQueryId}
          loading={historyLoading}
          onSelect={loadHistoryItem}
          onNewChat={handleNewChat}
          onDelete={handleDelete}
        />
        <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border">
          <AIChatPanel
            messages={messages}
            onMessagesChange={setMessages}
            onSend={async (msg) => {
              const res = await api.chat(msg);
              refreshHistory();
              if (res.query_id) {
                setActiveQueryId(res.query_id);
              }
              return res;
            }}
          />
        </div>
      </div>
    </div>
  );
}
