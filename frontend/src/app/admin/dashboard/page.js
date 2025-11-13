"use client";

import React, { useState } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import AdminCalendar from "@/components/AdminCalendar";
import AdminBookingList from "@/components/AdminBookingList";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export default function AdminDashboardPage() {
  return (
    <AdminProtectedRoute>
      <AdminDashboardContent />
    </AdminProtectedRoute>
  );
}

function AdminDashboardContent() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [cancellationSuggestions, setCancellationSuggestions] = useState(null);

  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">Admin Dashboard</h1>
      
      {/* Cancellation Suggestions Banner */}
      {cancellationSuggestions && cancellationSuggestions.suggestions.length > 0 && (
        <Card className="mb-6 border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-950">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-blue-900 dark:text-blue-100">
                  Slot Available - Potential Matches Found
                </CardTitle>
                <CardDescription className="text-blue-700 dark:text-blue-300">
                  A slot just opened at {new Date(cancellationSuggestions.cancelled_slot_time).toLocaleTimeString('en-US', { 
                    hour: 'numeric', 
                    minute: '2-digit',
                    hour12: true 
                  })}. Here are clients who might want to move up:
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCancellationSuggestions(null)}
                className="text-blue-700 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {cancellationSuggestions.suggestions.map((suggestion, index) => (
                <div 
                  key={suggestion.current_booking_id}
                  className="flex items-center justify-between p-3 bg-white dark:bg-zinc-800 rounded-lg border border-blue-200 dark:border-blue-800"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                        {suggestion.client_name}
                      </span>
                      <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
                        {Math.round(suggestion.match_score * 100)}% match
                      </span>
                    </div>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                      {suggestion.reason}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-1">
                      {suggestion.client_email}
                    </p>
                  </div>
                  <div className="ml-4 text-right">
                    <p className="text-xs text-zinc-500 dark:text-zinc-500">Current slot:</p>
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                      {new Date(suggestion.current_booking_time).toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true 
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-4">
              💡 Tip: Contact these clients to offer them the earlier time slot
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <AdminCalendar selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
        <AdminBookingList 
          selectedDate={selectedDate} 
          setCancellationSuggestions={setCancellationSuggestions}
        />
      </div>
    </main>
  );
}
