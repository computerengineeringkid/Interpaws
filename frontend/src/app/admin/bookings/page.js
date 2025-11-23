"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import AdminBookingList from "@/components/AdminBookingList";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";

export default function AdminBookingsPage() {
  // FIX: Use adminToken
  const { adminToken } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchBookings = async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().split('T')[0];
      const res = await fetch(`/bookings/${today}`, {
        // FIX: Use adminToken
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      
      if (!res.ok) throw new Error("Failed to fetch bookings");
      const data = await res.json();
      setBookings(data);
    } catch (err) {
      console.error(err);
      setError("Could not load bookings. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // FIX: Check adminToken
    if (adminToken) fetchBookings();
  }, [adminToken]);

  const handleDelete = async (id) => {
    if(!confirm("Are you sure you want to cancel this booking?")) return;
    try {
      const res = await fetch(`/bookings/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${adminToken}` } // FIX: Use adminToken
      });
      if(res.ok) {
        fetchBookings(); 
      }
    } catch(err) {
      alert("Failed to delete");
    }
  };

  return (
    <AdminProtectedRoute>
      <div className="space-y-6 p-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">All Bookings</h1>
          <button 
              onClick={fetchBookings}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
              Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-md border border-red-200">
            {error}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Scheduled Appointments</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Loading bookings...</div>
            ) : (
              <AdminBookingList bookings={bookings} onDelete={handleDelete} />
            )}
          </CardContent>
        </Card>
      </div>
    </AdminProtectedRoute>
  );
}