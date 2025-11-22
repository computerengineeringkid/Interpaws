"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { format } from "date-fns";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export default function AdminBookingList({ selectedDate, setCancellationSuggestions }) {
  const { adminToken } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [riskSnapshots, setRiskSnapshots] = useState({});
  const [riskLoading, setRiskLoading] = useState({});

  const fetchBookings = useCallback(async () => {
    if (!adminToken) return;
    
    setIsLoading(true);
    setError(null);

    try {
      const dateString = format(selectedDate, 'yyyy-MM-dd');
      const response = await fetch(`/api/bookings/${dateString}`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch bookings');
      }
      
      const data = await response.json();
      setBookings(data);
    } catch (err) {
      setError('Failed to fetch bookings.');
      console.error('Error fetching bookings:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedDate, adminToken]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  const fetchRisk = useCallback(async (bookingId) => {
    if (!adminToken) return;
    setRiskLoading((prev) => ({ ...prev, [bookingId]: true }));
    try {
      const response = await fetch(`/api/admin/bookings/${bookingId}/risk`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch risk');
      }

      const data = await response.json();
      setRiskSnapshots((prev) => ({ ...prev, [bookingId]: data }));
    } catch (err) {
      setRiskSnapshots((prev) => ({
        ...prev,
        [bookingId]: {
          risk_level: 'Unknown',
          risk_score: 0,
          reasoning: 'Risk data unavailable',
        },
      }));
      console.error('Error fetching risk score:', err);
    } finally {
      setRiskLoading((prev) => ({ ...prev, [bookingId]: false }));
    }
  }, [adminToken]);

  const prioritizedBookings = useMemo(() => {
    const upcoming = bookings
      .filter((booking) => new Date(booking.start_time) >= new Date())
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    return upcoming.slice(0, 5).map((b) => b.id);
  }, [bookings]);

  useEffect(() => {
    prioritizedBookings.forEach((bookingId) => {
      if (!riskSnapshots[bookingId] && !riskLoading[bookingId]) {
        fetchRisk(bookingId);
      }
    });
  }, [prioritizedBookings, fetchRisk, riskSnapshots, riskLoading]);

  const getRiskBadge = (bookingId) => {
    const snapshot = riskSnapshots[bookingId];
    if (!snapshot) {
      return (
        <Badge
          variant="secondary"
          className="animate-pulse"
          onMouseEnter={() => {
            if (!riskLoading[bookingId]) {
              fetchRisk(bookingId);
            }
          }}
        >
          …
        </Badge>
      );
    }

    const level = snapshot.risk_level || 'Unknown';
    const reasoning = snapshot.reasoning || 'No reasoning available';
    const palette = {
      Low: 'bg-emerald-100 text-emerald-700',
      Medium: 'bg-amber-100 text-amber-700',
      High: 'bg-red-100 text-red-700',
      Unknown: 'bg-slate-100 text-slate-600',
    };
    const iconMap = {
      Low: '🟢',
      Medium: '🟡',
      High: '🔴',
      Unknown: '⚪️',
    };

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            className={`${palette[level] || palette.Unknown} animate-fade-in`}
            onMouseEnter={() => {
              if (!riskSnapshots[bookingId] && !riskLoading[bookingId]) {
                fetchRisk(bookingId);
              }
            }}
          >
            {iconMap[level] || iconMap.Unknown} {level}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-left">
          {reasoning}
        </TooltipContent>
      </Tooltip>
    );
  };

  const handleDeleteBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to delete this booking?')) {
      return;
    }

    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete booking');
      }

      // Update local state without full refetch
      setBookings(prev => prev.filter(b => b.id !== bookingId));
    } catch (err) {
      setError('Failed to delete booking.');
      console.error('Error deleting booking:', err);
    }
  };

  const handleUpdateStatus = async (bookingId, newStatus) => {
    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) {
        throw new Error('Failed to update booking status');
      }

      // Update local state with the new status
      setBookings(prev => prev.map(b => 
        b.id === bookingId ? { ...b, status: newStatus } : b
      ));

      // If marking as completed, log AI feedback
      if (newStatus === 'completed') {
        fetch(`/api/log-feedback/?booking_id=${bookingId}`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${adminToken}`,
          },
        }).catch(err => {
          console.error('Failed to log AI feedback:', err);
        });
      }

      // Sprint 8: Dynamic Slot-Filling - Get cancellation suggestions
      if (newStatus === 'cancelled' && setCancellationSuggestions) {
        try {
          const suggestionsResponse = await fetch(`/api/admin/cancellation_suggestion/${bookingId}`, {
            headers: {
              Authorization: `Bearer ${adminToken}`,
            },
          });

          if (suggestionsResponse.ok) {
            const suggestionsData = await suggestionsResponse.json();
            
            // Only show suggestions if there are any
            if (suggestionsData.suggestions && suggestionsData.suggestions.length > 0) {
              setCancellationSuggestions(suggestionsData);
            }
          }
        } catch (err) {
          // Fail silently - suggestions are optional
          console.error('Failed to fetch cancellation suggestions:', err);
        }
      }
    } catch (err) {
      setError('Failed to update booking status.');
      console.error('Error updating booking status:', err);
    }
  };

  return (
    <TooltipProvider>
      <Card>
        <CardHeader>
          <CardTitle>Admin: Booking List</CardTitle>
        </CardHeader>
        <CardContent>
        {isLoading && <p>Loading...</p>}
        
        {error && <p className="text-red-500">{error}</p>}
        
        {!isLoading && !error && bookings.length === 0 && (
          <p>No bookings found for this date.</p>
        )}
        
        {!isLoading && !error && bookings.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Client ID</TableHead>
                <TableHead>Staff ID</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bookings.map((booking) => (
                <TableRow key={booking.id}>
                  <TableCell>{format(new Date(booking.start_time), 'HH:mm')}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-3">
                      <Select 
                        value={booking.status} 
                        onValueChange={(newStatus) => handleUpdateStatus(booking.id, newStatus)}
                      >
                        <SelectTrigger className="w-[150px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="confirmed">confirmed</SelectItem>
                          <SelectItem value="completed">completed</SelectItem>
                          <SelectItem value="cancelled">cancelled</SelectItem>
                        </SelectContent>
                      </Select>
                      {getRiskBadge(booking.id)}
                    </div>
                  </TableCell>
                  <TableCell>{booking.client_id}</TableCell>
                  <TableCell>{booking.staff_id}</TableCell>
                  <TableCell>
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => handleDeleteBooking(booking.id)}
                    >
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
