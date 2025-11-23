"use client";
import React, { useEffect, useState } from 'react';
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";

export default function AdminBookingList({ selectedDate, setCancellationSuggestions }) {
  const { adminToken } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!adminToken || !selectedDate) {
      setLoading(false);
      return;
    }

    const fetchBookings = async () => {
      setLoading(true);
      setError(null);
      try {
        const dateStr = selectedDate.toISOString().split('T')[0];
        const response = await fetch(`/api/bookings/${dateStr}`, {
          headers: { Authorization: `Bearer ${adminToken}` },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          throw new Error(errorData.detail || `Failed to fetch bookings: ${response.status}`);
        }
        const data = await response.json();
        setBookings(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Error fetching bookings:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchBookings();
  }, [adminToken, selectedDate]);

  const handleDelete = async (bookingId) => {
    if (!confirm("Are you sure you want to cancel this booking?")) return;

    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      if (!response.ok) throw new Error("Failed to cancel booking");
      
      // Refresh bookings
      setBookings(bookings.filter(b => b.id !== bookingId));
    } catch (err) {
      console.error("Error cancelling booking:", err);
      alert("Failed to cancel booking: " + err.message);
    }
  };
  
  // Helper for time formatting
  const formatTime = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  if (loading) {
    return (
      <Card className="flex flex-col items-center justify-center p-12 text-center bg-white">
        <div className="h-12 w-12 bg-zinc-100 rounded-full flex items-center justify-center mb-4 text-xl animate-pulse">📅</div>
        <p className="text-sm text-zinc-500">Loading appointments...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="flex flex-col items-center justify-center p-12 text-center bg-white border-red-200">
        <div className="h-12 w-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-xl">⚠️</div>
        <h3 className="text-lg font-medium text-red-900">Error loading appointments</h3>
        <p className="text-sm text-red-600">{error}</p>
      </Card>
    );
  }

  if (!bookings || bookings.length === 0) {
    return (
      <Card className="flex flex-col items-center justify-center p-12 text-center bg-white border-dashed">
        <div className="h-12 w-12 bg-zinc-100 rounded-full flex items-center justify-center mb-4 text-xl">📅</div>
        <h3 className="text-lg font-medium text-zinc-900">No appointments scheduled</h3>
        <p className="text-sm text-zinc-500">There are no bookings for this specific date.</p>
      </Card>
    );
  }

  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <table className="w-full text-left border-collapse">
        <thead className="bg-zinc-50/50 border-b">
          <tr>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider w-24">Time</th>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Patient</th>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Complaint</th>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Provider</th>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider text-center">Status</th>
            <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {bookings.map((booking) => {
            const statusColor = 
                booking.status === 'confirmed' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 
                booking.status === 'cancelled' ? 'bg-red-100 text-red-700 border-red-200' : 
                'bg-amber-100 text-amber-700 border-amber-200';

            return (
            <tr 
              key={booking.id} 
              onClick={(e) => {
                if (!e.target.closest('button')) {
                  window.location.href = `/admin/bookings/${booking.id}`;
                }
              }}
              className="group cursor-pointer hover:bg-zinc-50 transition-colors"
            >
              {/* Time */}
              <td className="py-4 px-4 whitespace-nowrap">
                <span className="font-mono text-sm font-semibold text-zinc-700">
                  {formatTime(booking.start_time)}
                </span>
              </td>

              {/* Patient */}
              <td className="py-4 px-4">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xs">
                        {booking.pet?.name?.substring(0,2).toUpperCase() || "??"}
                    </div>
                    <div>
                        <div className="font-medium text-zinc-900 text-sm">{booking.pet?.name || "Unknown"}</div>
                        <div className="text-xs text-zinc-500">{booking.client?.name}</div>
                    </div>
                </div>
              </td>

              {/* Complaint */}
              <td className="py-4 px-4">
                <p className="text-sm text-zinc-600 max-w-[200px] truncate" title={booking.complaint_reason}>
                    {booking.complaint_reason || "Check-up"}
                </p>
              </td>

              {/* Staff */}
              <td className="py-4 px-4">
                <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-indigo-500"></div>
                    <span className="text-sm text-zinc-700">Dr. {booking.staff?.name?.split(' ').pop() || "Unassigned"}</span>
                </div>
              </td>
              
              {/* Status */}
              <td className="py-4 px-4 text-center">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusColor} capitalize`}>
                  {booking.status}
                </span>
              </td>

              {/* Actions */}
              <td className="py-4 px-4 text-right">
                <button 
                  onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(booking.id);
                  }}
                  className="text-zinc-400 hover:text-red-600 text-xs font-medium px-2 py-1 rounded transition-colors"
                >
                  Cancel
                </button>
              </td>
            </tr>
          )})}
        </tbody>
      </table>
    </div>
  );
}