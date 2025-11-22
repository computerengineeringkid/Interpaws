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
          complaint_text: complaint || "No initial complaint provided"
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
    <div className="space-y-4">
      <ScrollArea className="h-[500px] w-full rounded-md border p-4 bg-white dark:bg-zinc-950">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground py-10">
              <p className="text-lg font-medium mb-2">👋 Welcome to Interpaws!</p>
              <p>I'm your AI Veterinary Intake Coordinator.</p>
              <p className="mt-2">Tell me how I can help your pet today (e.g., "My dog has a cough").</p>
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
                      ? "bg-primary text-primary-foreground max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm"
                      : "bg-muted text-foreground max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm whitespace-pre-wrap"
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
          placeholder={isLoading ? "Thinking..." : "Type your message..."}
          disabled={isLoading}
          className="flex-1"
        />
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Sending..." : "Send"}
        </Button>
      </form>
    </div>
  );
});

AIChat.displayName = "AIChat";

export default AIChat;
