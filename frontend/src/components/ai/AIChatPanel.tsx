"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { CitationChip } from "./CitationChip";
import { MarkdownContent } from "./MarkdownContent";
import type { Citation } from "@/lib/types";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  queryId?: number;
}

interface Props {
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
  onSend: (message: string) => Promise<{ response: string; citations: Citation[]; query_id?: number | null }>;
  placeholder?: string;
}

export function AIChatPanel({
  messages,
  onMessagesChange,
  onSend,
  placeholder = "Ask about movie recommendations...",
}: Props) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    const withUser: ChatMessage[] = [...messages, { role: "user", content: userMsg }];
    onMessagesChange(withUser);
    setLoading(true);
    try {
      const { response, citations, query_id } = await onSend(userMsg);
      onMessagesChange([
        ...withUser,
        { role: "assistant", content: response, citations, queryId: query_id ?? undefined },
      ]);
    } catch (e) {
      onMessagesChange([
        ...withUser,
        { role: "assistant", content: e instanceof Error ? e.message : "Something went wrong" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-12">
            <p className="text-lg mb-2">Ask me anything about your taste</p>
            <p className="text-sm">Try: &quot;Based on movies I watched last month, what should I watch next?&quot;</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <Card className={`max-w-[80%] ${msg.role === "user" ? "bg-primary/20" : ""}`}>
              <CardContent className="p-4">
                {msg.role === "assistant" ? (
                  <MarkdownContent content={msg.content} />
                ) : (
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {msg.citations.map((c) => (
                      <CitationChip key={c.movie_id} citation={c} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking... (usually 10–20 seconds)
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-border p-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder={placeholder}
          disabled={loading}
        />
        <Button onClick={handleSend} disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
