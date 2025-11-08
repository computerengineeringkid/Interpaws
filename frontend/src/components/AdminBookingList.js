"use client";

import React, { useState, useEffect } from "react";
import { format } from "date-fns/format";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

export default function AdminBookingList({ selectedDate }) {
  const [bookings, setBookings] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchBookings() {
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
    }

    fetchBookings();
  }, [selectedDate]);

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
              </TableRow>
            </TableHeader>
            <TableBody>
              {bookings.map((booking) => (
                <TableRow key={booking.id}>
                  <TableCell>{format(new Date(booking.start_time), 'HH:mm')}</TableCell>
                  <TableCell>{booking.status}</TableCell>
                  <TableCell>{booking.client_id}</TableCell>
                  <TableCell>{booking.staff_id}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
