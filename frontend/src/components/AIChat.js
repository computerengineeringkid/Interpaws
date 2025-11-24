"use client";

import { useState, useEffect, forwardRef, useImperativeHandle } from "react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Calendar } from "@/components/ui/calendar";
import { fetchWithAuth } from "@/utils/api";

const AIChat = forwardRef(({ token, context, startSignal = 0, onBookingComplete }, ref) => {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeContext, setActiveContext] = useState(null);

  useImperativeHandle(ref, () => ({
    getChatHistory: () => messages.map((m) => `${m.role === "user" ? "Client" : "AI"}: ${m.content}`).join("\n"),
  }));

  useEffect(() => {
    if (!startSignal) return;
    if (!context || !context.complaint?.trim()) return;

    setMessages([]);
    setActiveContext(context);
    const initialPrompt = `Owner: ${context.ownerName}. Pet: ${context.petName}. Complaint: ${context.complaint}. Infer the service type and propose bookable appointment slots.`;
    sendPrompt(initialPrompt, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startSignal]);

  const sendPrompt = async (text, skipUserEcho = false) => {
    if (!text.trim()) return;
    setIsLoading(true);

    if (!skipUserEcho) {
      const userMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMessage]);
    }

    try {
      const res = await fetchWithAuth("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: text,
          complaint_text: activeContext?.complaint || context?.complaint || "No complaint provided",
          // Persistent Context Pattern: send pet and owner every turn
          pet_name: activeContext?.petName,
          owner_name: activeContext?.ownerName,
        }),
      });

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const result = await res.json();
      const aiMessage = {
        role: "ai",
        content: result?.response ?? "",
        slots: result?.slots ?? [],
        serviceType: result?.service_type,
        uiAction: result?.ui_action,
        suggestedDate: result?.suggested_date,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage = { role: "ai", content: "Sorry, I couldn't process that. Please try again." };
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

  const handleSlotSelection = async (slot, serviceTypeHint) => {
    if (!activeContext) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Please start the chat with your pet details before booking." },
      ]);
      return;
    }

    if (!token) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Please log in to book this slot." },
      ]);
      return;
    }

    try {
      const response = await fetchWithAuth("/api/bookings/by-name", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          owner_name: activeContext?.ownerName,
          pet_name: activeContext?.petName,
          service_type: serviceTypeHint || "urgent care",
          preferred_time: slot.start_time,
          complaint_reason: activeContext?.complaint,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Booking failed" }));
        throw new Error(error.detail || "Booking failed");
      }

      const confirmation = await response.json();
      const message = `Booked ${activeContext?.petName} on ${confirmation?.start_time ? new Date(confirmation.start_time).toLocaleString() : "the scheduled time"}.`;
      setMessages((prev) => [...prev, { role: "ai", content: message }]);
      if (onBookingComplete) {
        onBookingComplete(message);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: err.message || "Unable to book that slot." },
      ]);
    }
  };

  const handleCalendarDateSelect = (date) => {
    if (!date) return;
    const formattedDate = date.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    sendPrompt(`What time slots do you have on ${formattedDate}?`);
  };

  return (
    <div className="space-y-4">
      <ScrollArea className="h-[500px] w-full rounded-md border p-4 bg-white dark:bg-zinc-950">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground py-10">
              <p className="text-lg font-medium mb-2">Welcome to Interpaws!</p>
              <p>I&apos;m your AI Veterinary Intake Coordinator.</p>
              <p className="mt-2">Tell me how I can help your pet today (e.g., &quot;My dog has a cough&quot;).</p>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={
                    m.role === "user"
                      ? "bg-primary text-primary-foreground max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm"
                      : "bg-muted text-foreground max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm whitespace-pre-wrap"
                  }
                >
                  {m.content}
                  {m?.uiAction === "show_calendar" && (
                    <div className="mt-3 flex justify-center">
                      <Calendar
                        mode="single"
                        onSelect={handleCalendarDateSelect}
                        disabled={(date) => date < new Date()}
                        className="rounded-md border bg-background"
                      />
                    </div>
                  )}
                  {m?.slots && m.slots.length > 0 && !m?.uiAction && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {m.slots.map((slot, slotIdx) => {
                        const slotStart = slot?.start_time;
                        if (!slotStart) return null;
                        return (
                          <Button
                            key={`${slotStart}-${slotIdx}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleSlotSelection(slot, m?.serviceType)}
                          >
                            {new Date(slotStart).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
                            {slot?.staff_name ? ` • ${slot.staff_name}` : ""}
                          </Button>
                        );
                      })}
                    </div>
                  )}
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
