"use client";

import React, { useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { format } from "date-fns";

export default function MyBookingsPage() {
  const [bookings, setBookings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchBookings = async () => {
      try {
        const res = await fetch("/api/bookings/client/1");
        if (!res.ok) {
          throw new Error(`Failed to load bookings (${res.status})`);
        }
        const data = await res.json();
        if (active) setBookings(data || []);
      } catch (e) {
        if (active) setError(e.message || "Failed to load bookings");
      } finally {
        if (active) setIsLoading(false);
      }
    };
    fetchBookings();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="container mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">My Bookings</h1>

      {isLoading && <p>Loading...</p>}
      {error && <p className="text-red-600">{error}</p>}

      <div className="grid gap-4">
        {bookings.map((booking) => {
          const start = new Date(booking.start_time);
          const title = isNaN(start)
            ? "Scheduled"
            : `${format(start, "EEE, MMM d yyyy p")}`;
          return (
            <Card key={booking.id}>
              <CardHeader>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>Status: {booking.status}</p>
                <p>Staff ID: {booking.staff_id}</p>
              </CardContent>
            </Card>
          );
        })}
        {!isLoading && !error && bookings.length === 0 && (
          <p>No bookings yet.</p>
        )}
      </div>
    </main>
  );
}
