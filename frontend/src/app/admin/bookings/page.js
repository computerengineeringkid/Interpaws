"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import { fetchWithAuth } from "@/utils/api";
import { cn } from "@/lib/utils";

export default function AdminBookingsPage() {
  // CRITICAL FIX: Use adminToken, NOT token
  const { adminToken } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null); // null = show all upcoming
  const [viewMode, setViewMode] = useState("upcoming"); // "upcoming" or "specific"

  const fetchBookings = async (specificDate = null) => {
    if (!adminToken) return;

    try {
      setLoading(true);
      setError(null);

      if (specificDate) {
        // Fetch bookings for a specific date
        const dateStr = specificDate.toISOString().split('T')[0];
        const res = await fetchWithAuth(`/api/bookings/${dateStr}`, {
          headers: { Authorization: `Bearer ${adminToken}` },
        });
        const data = res.ok ? await res.json() : [];
        setBookings(Array.isArray(data) ? data : []);
      } else {
        // Fetch bookings for the next 7 days to show upcoming appointments
        const promises = [];
        for (let i = 0; i < 7; i++) {
          const date = new Date();
          date.setDate(date.getDate() + i);
          const dateStr = date.toISOString().split('T')[0];
          promises.push(
            fetchWithAuth(`/api/bookings/${dateStr}`, {
              headers: { Authorization: `Bearer ${adminToken}` },
            }).then(res => res.ok ? res.json() : [])
          );
        }

        const results = await Promise.all(promises);
        const allBookings = results.flat();
        setBookings(Array.isArray(allBookings) ? allBookings : []);
      }
    } catch (err) {
      console.error(err);
      setError("Could not load bookings. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) {
      if (viewMode === "specific" && selectedDate) {
        fetchBookings(selectedDate);
      } else {
        fetchBookings(null);
      }
    }
  }, [adminToken, viewMode, selectedDate]);

  const handleDateSelect = (date) => {
    if (date) {
      setSelectedDate(date);
      setViewMode("specific");
    }
  };

  const handleShowUpcoming = () => {
    setViewMode("upcoming");
    setSelectedDate(null);
  };

  const handleDelete = async (id) => {
    if(!confirm("Are you sure you want to cancel this booking?")) return;
    try {
      const res = await fetchWithAuth(`/api/bookings/${id}`, {
        method: 'DELETE',
        // CRITICAL FIX: Use adminToken
        headers: { Authorization: `Bearer ${adminToken}` }
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
              onClick={() => fetchBookings(viewMode === "specific" ? selectedDate : null)}
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
          <CardHeader className="space-y-4">
            <CardTitle>
              {viewMode === "upcoming"
                ? "Upcoming Appointments (Next 7 Days)"
                : `Appointments for ${selectedDate?.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
              }
            </CardTitle>

            {/* Date Filter Controls */}
            <div className="flex items-center gap-4 pt-2">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Filter by date:
                </label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "justify-start text-left font-normal",
                        !selectedDate && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {selectedDate ? (
                        selectedDate.toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })
                      ) : (
                        <span>Pick a date</span>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={selectedDate}
                      onSelect={handleDateSelect}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>

              {viewMode === "specific" && (
                <Button
                  variant="link"
                  onClick={handleShowUpcoming}
                  className="text-sm"
                >
                  Show upcoming (next 7 days)
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Loading bookings...</div>
            ) : bookings.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center">
                <div className="h-12 w-12 bg-zinc-100 rounded-full flex items-center justify-center mb-4 text-xl">📅</div>
                <h3 className="text-lg font-medium text-zinc-900">No appointments scheduled</h3>
                <p className="text-sm text-zinc-500">
                  {viewMode === "upcoming"
                    ? "There are no bookings in the next 7 days."
                    : "There are no bookings for this date."
                  }
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-zinc-50/50 border-b">
                    <tr>
                      <th className="py-3 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Date & Time</th>
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

                      const formatDateTime = (dateString) => {
                        if (!dateString) return "N/A";
                        const date = new Date(dateString);
                        return date.toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          weekday: 'short'
                        }) + ' ' + date.toLocaleTimeString('en-US', {
                          hour: 'numeric',
                          minute: '2-digit',
                          hour12: true
                        });
                      };

                      return (
                        <tr
                          key={booking.id}
                          className="group hover:bg-zinc-50 transition-colors"
                        >
                          {/* Date & Time */}
                          <td className="py-4 px-4 whitespace-nowrap">
                            <span className="font-mono text-sm font-semibold text-zinc-700">
                              {formatDateTime(booking.start_time)}
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
                            <Badge className={`${statusColor} capitalize`}>
                              {booking.status}
                            </Badge>
                          </td>

                          {/* Actions */}
                          <td className="py-4 px-4 text-right">
                            <button
                              onClick={() => handleDelete(booking.id)}
                              className="text-zinc-400 hover:text-red-600 text-xs font-medium px-2 py-1 rounded transition-colors"
                            >
                              Cancel
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AdminProtectedRoute>
  );
}
