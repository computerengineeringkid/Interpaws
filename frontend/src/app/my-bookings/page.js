'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MyBookingsPage() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        const response = await fetch('/api/bookings/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        if (response.ok) {
          const data = await response.json();
          setBookings(data);
        } else {
          console.error('Failed to fetch bookings');
        }
      } catch (error) {
        console.error('Error fetching bookings:', error);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchBookings();
    }
  }, [token]);

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-8">
          <p>Loading your bookings...</p>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">My Bookings</h1>
        {bookings.length === 0 ? (
          <p>You have no bookings yet.</p>
        ) : (
          <div className="grid gap-4">
            {bookings.map((booking) => (
              <Card key={booking.id}>
                <CardHeader>
                  <CardTitle>Booking #{booking.id}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p><strong>Start:</strong> {new Date(booking.start_time).toLocaleString()}</p>
                  <p><strong>End:</strong> {new Date(booking.end_time).toLocaleString()}</p>
                  <p><strong>Status:</strong> {booking.status}</p>
                  {booking.staff_id && <p><strong>Staff ID:</strong> {booking.staff_id}</p>}
                  {booking.pet_id && <p><strong>Pet ID:</strong> {booking.pet_id}</p>}
                  {booking.complaint_reason && <p><strong>Complaint:</strong> {booking.complaint_reason}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
