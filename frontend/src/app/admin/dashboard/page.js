"use client";

import React, { useState, useEffect } from "react";
// REMOVED: import Navigation from "@/components/Navigation"; 
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import AdminCalendar from "@/components/AdminCalendar";
import AdminBookingList from "@/components/AdminBookingList";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";

export default function AdminDashboardPage() {
  return (
    <AdminProtectedRoute>
      {/* The AdminLayout (frontend/src/app/admin/layout.js) already provides:
         1. The <AdminNav />
         2. The background color (bg-zinc-50)
         3. The min-height
         
         So we only need to render the content here.
      */}
      <AdminDashboardContent />
    </AdminProtectedRoute>
  );
}

function AdminDashboardContent() {
  const { adminToken } = useAuth();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [cancellationSuggestions, setCancellationSuggestions] = useState(null);
  const [forecastItems, setForecastItems] = useState([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState(null);

  useEffect(() => {
    if (!adminToken) return;

    const fetchForecast = async () => {
      setForecastLoading(true);
      setForecastError(null);
      try {
        const response = await fetch("/api/admin/inventory/forecast", {
          headers: {
            Authorization: `Bearer ${adminToken}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch inventory forecast");
        }

        const data = await response.json();
        setForecastItems(data);
      } catch (err) {
        setForecastError("Unable to load inventory forecast.");
        console.error("Inventory forecast error:", err);
      } finally {
        setForecastLoading(false);
      }
    };

    fetchForecast();
  }, [adminToken]);

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

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>📉 Inventory Forecast</CardTitle>
          <CardDescription>Usage velocity for the last 30 days.</CardDescription>
        </CardHeader>
        <CardContent>
          {forecastLoading && <p>Analyzing recent inventory usage...</p>}

          {!forecastLoading && forecastError && (
            <p className="text-sm text-red-600 dark:text-red-400">{forecastError}</p>
          )}

          {!forecastLoading && !forecastError && forecastItems.length === 0 && (
            <p className="text-sm text-zinc-600 dark:text-zinc-300">Inventory healthy.</p>
          )}

          {!forecastLoading && !forecastError && forecastItems.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead className="text-right">Days Left</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forecastItems.map((item, index) => {
                  const urgent = item.days_remaining < 7;
                  const formattedUsage = Number(item.daily_usage).toFixed(2);
                  const formattedDays = Number(item.days_remaining).toFixed(1);
                  return (
                    <TableRow key={`${item.medication_name}-${index}`}>
                      <TableCell>
                        <div className="font-medium text-zinc-900 dark:text-zinc-100">{item.medication_name}</div>
                        <div className="text-xs text-zinc-500 dark:text-zinc-400">
                          Stock: {item.current_stock} • {formattedUsage} / day
                        </div>
                      </TableCell>
                      <TableCell className={`text-right text-sm ${urgent ? "text-red-600 dark:text-red-400 font-semibold" : "text-amber-600 dark:text-amber-400"}`}>
                        {formattedDays} days
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </main>
  );
}