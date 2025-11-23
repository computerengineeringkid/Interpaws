"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import AdminBookingList from "@/components/AdminBookingList";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminBookingsPage() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch all bookings (using a date range or all if supported)
  const fetchBookings = async () => {
    try {
      setLoading(true);
      // NOTE: Ensure your backend supports GET /bookings/me or similar. 
      // If listing ALL for admin, you might need to hit /bookings/2025-11-24 (today)
      // For now, let's verify with today's date which we know works:
      const today = new Date().toISOString().split('T')[0];
      const res = await fetch(`/bookings/${today}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setBookings(data);
      }
    } catch (err) {
      console.error("Failed to load bookings", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchBookings();
  }, [token]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">All Bookings</h1>
        <button 
          onClick={fetchBookings}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Today's Appointments</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-4">Loading...</div>
          ) : (
            <AdminBookingList bookings={bookings} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}