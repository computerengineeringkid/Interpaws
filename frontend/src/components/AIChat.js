"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function AIChat() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);

    // Add user message immediately
    const userMessage = { role: "user", content: prompt };
    setMessages((prev) => [...prev, userMessage]);

    // Clear input
    setPrompt("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userMessage.content }),
      });

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const result = await res.json();
      const aiMessage = { role: "ai", content: result.response };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage = { role: "ai", content: "Sorry, I couldn't process that. Please try again." };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className="mt-8">
      <CardHeader>
        <CardTitle className="text-xl">AI Chat</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <ScrollArea className="h-64 w-full rounded-md border p-3">
            <div className="space-y-3">
              {messages.length === 0 ? (
                <div className="text-sm text-muted-foreground">Start a conversation by typing a prompt below.</div>
              ) : (
                messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={
                      m.role === "user"
                        ? "flex justify-end"
                        : "flex justify-start"
                    }
                  >
                    <div
                      className={
                        m.role === "user"
                          ? "bg-primary text-primary-foreground max-w-[80%] rounded-lg px-3 py-2 text-sm"
                          : "bg-muted text-foreground max-w-[80%] rounded-lg px-3 py-2 text-sm"
                      }
                    >
                      {m.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={isLoading ? "Thinking..." : "Ask me anything about your pet or bookings"}
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Sending..." : "Send"}
            </Button>
          </form>
        </div>
      </CardContent>
    </Card>
  );
}
