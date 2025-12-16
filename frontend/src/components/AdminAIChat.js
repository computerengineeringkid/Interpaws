"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { fetchWithAuth } from "@/utils/api";
import { useAuth } from "@/context/AuthContext";
import { MessageSquare, Send, Sparkles, Calendar, Package, Activity, BarChart3 } from "lucide-react";

export default function AdminAIChat() {
  const { adminToken } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `staff_${Math.random().toString(36).substring(7)}`);

  const sendPrompt = async (text) => {
    if (!text.trim() || !adminToken) return;
    setIsLoading(true);

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Single API call to the staff agent endpoint
      const res = await fetchWithAuth("/api/staff/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${adminToken}`
        },
        body: JSON.stringify({
          prompt: text,
          session_id: sessionId,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        const aiMessage = {
          role: "ai",
          content: result.response || "I couldn't process that request.",
          data: result.data,
          intent: result.intent,
          suggestions: result.suggestions,
        };
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        const errorMessage = {
          role: "ai",
          content: "Sorry, I couldn't process that request. Please try again.",
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (err) {
      console.error("Staff AI error:", err);
      const errorMessage = {
        role: "ai",
        content: "Sorry, I couldn't process that request. Please make sure you're logged in as an admin.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await sendPrompt(prompt);
    setPrompt("");
  };

  const quickActions = [
    { label: "Today's Schedule", prompt: "What's my schedule today?", icon: Calendar },
    { label: "Check Inventory", prompt: "What medications are running low?", icon: Package },
    { label: "Triage Help", prompt: "A dog is vomiting, how urgent is this?", icon: Activity },
    { label: "Weekly Stats", prompt: "How many appointments this week?", icon: BarChart3 },
  ];

  // Render suggestion buttons
  const renderSuggestions = (suggestions) => {
    if (!suggestions || suggestions.length === 0) return null;
    return (
      <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-600">
        <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2">Quick actions:</p>
        <div className="flex flex-wrap gap-2">
          {suggestions.slice(0, 3).map((suggestion, idx) => (
            <Button
              key={idx}
              variant="outline"
              size="sm"
              onClick={() => sendPrompt(suggestion)}
              disabled={isLoading}
              className="text-xs h-7 bg-zinc-50 dark:bg-zinc-900"
            >
              {suggestion}
            </Button>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-zinc-50/50 dark:bg-zinc-900">
      {/* Header */}
      <div className="border-b bg-white dark:bg-zinc-950 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">AI Staff Assistant</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Schedule, patients, inventory, triage & analytics</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-6 bg-zinc-50/50 dark:bg-zinc-900 min-h-[400px] max-h-[500px]">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900 mb-4">
                <MessageSquare className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h4 className="font-medium text-zinc-900 dark:text-zinc-50 mb-2">How can I help you today?</h4>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
                I can help with schedules, patients, inventory, triage, and more
              </p>
              <div className="grid grid-cols-2 gap-3 max-w-lg mx-auto">
                {quickActions.map((action, idx) => {
                  const Icon = action.icon;
                  return (
                    <Button
                      key={idx}
                      variant="outline"
                      size="lg"
                      onClick={() => sendPrompt(action.prompt)}
                      className="h-auto py-4 flex flex-col items-start gap-2 text-left bg-white dark:bg-zinc-950 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                      disabled={isLoading}
                    >
                      <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      <span className="text-sm font-medium">{action.label}</span>
                    </Button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    m.role === "user"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-sm border border-zinc-200 dark:border-zinc-700"
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</div>

                  {/* Render suggestions for AI messages */}
                  {m.role === "ai" && renderSuggestions(m.suggestions)}
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-zinc-800 rounded-2xl px-4 py-3 shadow-sm border border-zinc-200 dark:border-zinc-700">
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                  <span className="text-sm text-zinc-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t bg-white dark:bg-zinc-950 p-4">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <Input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={isLoading ? "Processing..." : "Ask about schedules, patients, inventory, triage..."}
            disabled={isLoading}
            className="flex-1 bg-zinc-50 dark:bg-zinc-900"
          />
          <Button type="submit" disabled={isLoading || !prompt.trim()} className="gap-2">
            <Send className="h-4 w-4" />
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}
