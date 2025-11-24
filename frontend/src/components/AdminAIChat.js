"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { fetchWithAuth } from "@/utils/api";
import { useAuth } from "@/context/AuthContext";
import { MessageSquare, Send, Sparkles, Calendar } from "lucide-react";

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
      // Get today's date for staff queries
      const today = new Date().toISOString().split('T')[0];

      // Staff AI: Hybrid approach - fetch real data and provide conversational context
      let responseText = "";
      let fetchedData = "";

      // Extract date from query - improved parsing
      let queryDate = today;

      // Try to match various date formats
      // "Tuesday the 25th", "the 25th", "25th", "check 25", etc.
      // Optionally match day name, then optional "the", then day number with optional ordinal suffix
      const dayMatch = text.match(/(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)?\s*(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?/i);

      if (dayMatch) {
        const day = parseInt(dayMatch[1]);
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth();

        // Create date for the specified day in the current month
        currentDate.setDate(day);
        queryDate = currentDate.toISOString().split('T')[0];
      }

      // Handle schedule queries (today, specific date, recent, upcoming)
      // Added "check", "recent", "upcoming" as schedule keywords
      const isScheduleQuery = text.toLowerCase().includes("appointment") ||
                             text.toLowerCase().includes("schedule") ||
                             text.toLowerCase().includes("booking") ||
                             text.toLowerCase().includes("patient") ||
                             text.toLowerCase().includes("check") ||
                             text.toLowerCase().includes("recent") ||
                             text.toLowerCase().includes("upcoming");

      if (isScheduleQuery) {
        try {
          // Check if asking for specific date or today's schedule
          const isSpecificDate = dayMatch && !text.toLowerCase().includes("today");
          const dateToFetch = isSpecificDate ? queryDate : today;

          const bookingsRes = await fetchWithAuth(`/api/bookings/staff/my-schedule/${dateToFetch}`, {
            headers: { Authorization: `Bearer ${adminToken}` },
          });

          if (bookingsRes.ok) {
            const bookings = await bookingsRes.json();
            const dateStr = new Date(dateToFetch).toLocaleDateString('en-US', {weekday: 'long', month: 'long', day: 'numeric'});

            if (Array.isArray(bookings) && bookings.length > 0) {
              fetchedData = `\n\n📅 Your Schedule for ${dateStr}:\n\nYou have ${bookings.length} ${bookings.length === 1 ? 'patient' : 'patients'} scheduled:\n\n` +
                bookings.map(b =>
                  `• ${new Date(b.start_time).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'})} - ${b.pet?.name || 'Unknown'} (${b.client?.name || 'Unknown'})${b.complaint_reason ? '\n  Reason: ' + b.complaint_reason : ''}`
                ).join('\n\n');
              responseText = ""; // Will use AI to respond
            } else {
              fetchedData = `\n\n📅 You have no appointments scheduled for ${dateStr}.`;
              responseText = "";
            }
          }
        } catch (err) {
          console.error("Error fetching bookings:", err);
          responseText = "Sorry, I couldn't fetch the schedule. Please try again.";
        }
      }

      // Handle pet/client info queries
      const petInfoMatch = text.match(/(?:about|info|information|tell me about|details|show me)\s+(?:for\s+)?([A-Z][a-z]+)/i);
      if (petInfoMatch && !responseText && !fetchedData) {
        const searchName = petInfoMatch[1];
        try {
          const petsRes = await fetchWithAuth(`/api/pets/search?pet_name=${encodeURIComponent(searchName)}`, {
            headers: { Authorization: `Bearer ${adminToken}` },
          });
          if (petsRes.ok) {
            const pets = await petsRes.json();
            if (Array.isArray(pets) && pets.length > 0) {
              fetchedData = `\n\n🐾 Found ${pets.length} ${pets.length === 1 ? 'match' : 'matches'} for "${searchName}":\n\n` +
                pets.slice(0, 3).map(p => {
                  let info = `**${p.name}** (${p.species}${p.breed ? ', ' + p.breed : ''})\n`;
                  info += `Owner: ${p.owner_name || 'Unknown'}\n`;
                  info += `Contact: ${p.owner_email || 'N/A'}\n`;
                  info += `Age: ${p.age || 'Unknown'}`;
                  if (p.date_of_birth) {
                    info += `\nDate of Birth: ${new Date(p.date_of_birth).toLocaleDateString()}`;
                  }
                  return info;
                }).join('\n\n---\n\n');
              responseText = "";
            } else {
              fetchedData = `\n\nNo pets found matching "${searchName}".`;
              responseText = "";
            }
          }
        } catch (err) {
          console.error("Error fetching pet info:", err);
          responseText = `Sorry, I couldn't find information for "${searchName}". Please try again.`;
        }
      }

      // Handle medication/inventory queries
      if ((text.toLowerCase().includes("medication") || text.toLowerCase().includes("inventory") || text.toLowerCase().includes("stock")) && !responseText && !fetchedData) {
        try {
          const medsRes = await fetchWithAuth(`/api/medications`, {
            headers: { Authorization: `Bearer ${adminToken}` },
          });
          if (medsRes.ok) {
            const medications = await medsRes.json();
            if (Array.isArray(medications) && medications.length > 0) {
              const lowStock = medications.filter(m => m.stock_quantity < 50);
              const outOfStock = medications.filter(m => m.stock_quantity === 0);

              fetchedData = `\n\n💊 **Medication Inventory Report**\n\nTotal medications tracked: ${medications.length}\n`;

              if (outOfStock.length > 0) {
                fetchedData += `\n⚠️ **OUT OF STOCK** (${outOfStock.length} items):\n` +
                  outOfStock.slice(0, 5).map(m => `• ${m.name} - ${m.stock_quantity} ${m.unit}`).join('\n');
                if (outOfStock.length > 5) {
                  fetchedData += `\n• ... and ${outOfStock.length - 5} more`;
                }
              }

              if (lowStock.length > 0 && outOfStock.length < medications.length) {
                const lowStockInStock = lowStock.filter(m => m.stock_quantity > 0);
                if (lowStockInStock.length > 0) {
                  fetchedData += `\n\n⚡ **LOW STOCK** (${lowStockInStock.length} items):\n` +
                    lowStockInStock.slice(0, 5).map(m =>
                      `• ${m.name} - ${m.stock_quantity} ${m.unit}`
                    ).join('\n');
                  if (lowStockInStock.length > 5) {
                    fetchedData += `\n• ... and ${lowStockInStock.length - 5} more`;
                  }
                }
              }

              if (outOfStock.length === 0 && lowStock.length === 0) {
                fetchedData += `\n\n✅ All medications are well-stocked!`;
              }
              responseText = "";
            } else {
              fetchedData = `\n\n💊 No medications are currently tracked in the inventory system.`;
              responseText = "";
            }
          }
        } catch (err) {
          console.error("Error fetching medications:", err);
          responseText = "Sorry, I couldn't fetch the medication inventory. Please try again.";
        }
      }

      // If we have fetched data, use AI to provide conversational response with the data
      if (fetchedData && !responseText) {
        try {
          const res = await fetchWithAuth("/api/agent/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${adminToken}`
            },
            body: JSON.stringify({
              prompt: `[STAFF QUERY] ${text}\n\nContext: You are assisting a veterinary clinic STAFF MEMBER (NOT a client). Respond as a professional colleague providing operational information. Below is REAL data from the database. Provide a brief (1 sentence max) professional acknowledgment, then let the data speak for itself. Do NOT give client-facing advice or recommendations. Keep it factual and concise.\n\nDATA:${fetchedData}`,
              session_id: sessionId,
              complaint_text: "Staff assistance",
              owner_name: "Staff Member",
              pet_name: null,
            }),
          });

          if (res.ok) {
            const result = await res.json();
            responseText = (result?.response || "") + fetchedData;
          } else {
            responseText = fetchedData;
          }
        } catch (err) {
          console.error("Error getting conversational response:", err);
          responseText = fetchedData;
        }
      }

      // Default response if no specific query matched
      if (!responseText && !fetchedData) {
        responseText = "I can help you with:\n• Today's appointments and schedule\n• Patient information (try: 'Tell me about [pet name]')\n• Medication inventory and stock levels\n\nWhat would you like to know?";
      }

      const aiMessage = {
        role: "ai",
        content: responseText,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage = {
        role: "ai",
        content: "Sorry, I couldn't process that request. Please make sure you're logged in as an admin."
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
    { label: "Today's Schedule", prompt: "Show me today's appointments", icon: Calendar },
    { label: "Check Inventory", prompt: "What medications are low in stock?", icon: Sparkles },
    { label: "Upcoming Surgeries", prompt: "What surgeries are scheduled this week?", icon: MessageSquare },
    { label: "Recent Bookings", prompt: "What are the recent bookings?", icon: Calendar },
  ];

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
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Ask about schedules, patients, inventory & operations</p>
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
                I can assist with clinic operations, schedules, and more
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

                  {/* Display appointment slots if available */}
                  {m?.slots && m.slots.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-600 space-y-2">
                      <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Available Slots:</p>
                      <div className="space-y-1">
                        {m.slots.map((slot, slotIdx) => {
                          const slotStart = slot?.start_time;
                          if (!slotStart) return null;
                          return (
                            <div
                              key={`${slotStart}-${slotIdx}`}
                              className="flex items-center gap-2 text-xs bg-zinc-50 dark:bg-zinc-900 p-2 rounded-md"
                            >
                              <Calendar className="h-3 w-3 text-zinc-400" />
                              <span>
                                {new Date(slotStart).toLocaleString([], {
                                  month: "short",
                                  day: "numeric",
                                  hour: "numeric",
                                  minute: "2-digit",
                                })}
                              </span>
                              {slot?.staff_name && (
                                <span className="ml-auto text-zinc-500">• {slot.staff_name}</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
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
            placeholder={isLoading ? "Processing..." : "Ask about operations, schedules, inventory..."}
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
