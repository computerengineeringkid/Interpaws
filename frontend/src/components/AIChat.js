"use client";

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

const AIChat = forwardRef(({ complaint }, ref) => {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [triageInitiated, setTriageInitiated] = useState(false);

  // Expose getChatHistory method to parent component via ref
  useImperativeHandle(ref, () => ({
    getChatHistory: () => {
      // Return formatted chat history as a single string
      return messages.map(m => `${m.role === 'user' ? 'Client' : 'AI'}: ${m.content}`).join('\n');
    }
  }));

  // Auto-trigger triage when complaint changes
  useEffect(() => {
    async function initiateTriage() {
      // Only trigger if we have a complaint, messages are empty, and we haven't initiated triage yet
      if (complaint && complaint.trim() && messages.length === 0 && !triageInitiated) {
        setTriageInitiated(true);
        setIsLoading(true);

        try {
          const res = await fetch("/api/chat/triage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ complaint_text: complaint }),
          });

          if (!res.ok) {
            throw new Error(`Request failed with status ${res.status}`);
          }

          const result = await res.json();
          const aiMessage = { role: "ai", content: result.response };
          setMessages([aiMessage]);
        } catch (err) {
          const errorMessage = { role: "ai", content: "Sorry, I couldn't start the triage process. Please try again." };
          setMessages([errorMessage]);
        } finally {
          setIsLoading(false);
        }
      }
    }

    initiateTriage();
  }, [complaint, messages.length, triageInitiated]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;

    // Check if complaint text is provided
    if (!complaint || !complaint.trim()) {
      const warningMessage = { 
        role: "ai", 
        content: "Please describe your pet's issue in the booking form above first, so I can provide personalized assistance." 
      };
      setMessages((prev) => [...prev, warningMessage]);
      return;
    }

    setIsLoading(true);

    // Add user message immediately
    const userMessage = { role: "user", content: prompt };
    setMessages((prev) => [...prev, userMessage]);

    // Clear input
    setPrompt("");

    try {
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt: userMessage.content,
          complaint_text: complaint
        }),
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
                <div className="text-sm text-muted-foreground">
                  {complaint && complaint.trim() 
                    ? "Starting AI triage interview..."
                    : "Please describe your pet's issue in the booking form above, then I'll ask you some questions to help better understand the situation."}
                </div>
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
              placeholder={isLoading ? "Thinking..." : "Answer the AI's questions or ask your own..."}
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
});

AIChat.displayName = "AIChat";

export default AIChat;
