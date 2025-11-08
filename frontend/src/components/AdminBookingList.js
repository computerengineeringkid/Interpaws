"use client";

import React, { useState, useEffect, useCallback } from "react";
import { format } from "date-fns/format";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

export default function AdminBookingList({ selectedDate }) {
  const [bookings, setBookings] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchBookings = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const dateString = format(selectedDate, 'yyyy-MM-dd');
      const response = await fetch(`/api/bookings/${dateString}`);
      
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
  }, [selectedDate]);

  useEffect(() => {
    fetchBookings();
  }, [selectedDate, fetchBookings]);

  const handleDeleteBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to delete this booking?')) {
      return;
    }

    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: 'DELETE',
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
    } catch (err) {
      setError('Failed to update booking status.');
      console.error('Error updating booking status:', err);
    }
  };

  return (
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
  );
}
