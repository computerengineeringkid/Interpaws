'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function MyBookingsPage() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [rescheduleOptions, setRescheduleOptions] = useState([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [rescheduleError, setRescheduleError] = useState(null);
  const [optionSubmitting, setOptionSubmitting] = useState(null);

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
          setError(null);
        } else {
          setError('Failed to load bookings. Please try again.');
        }
      } catch (error) {
        setError('Unable to connect. Please check your network.');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchBookings();
    }
  }, [token]);

  const openRescheduleModal = async (booking) => {
    setSelectedBooking(booking);
    setRescheduleOptions([]);
    setRescheduleError(null);
    setRescheduleModalOpen(true);
    setOptionsLoading(true);
    try {
      const response = await fetch(`/api/bookings/${booking.id}/reschedule_options`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch smart options');
      }

      const data = await response.json();
      setRescheduleOptions(data);
    } catch (err) {
      setRescheduleError('Unable to load smart options. Please try again.');
      console.error('Error loading reschedule options:', err);
    } finally {
      setOptionsLoading(false);
    }
  };

  const closeRescheduleModal = () => {
    setRescheduleModalOpen(false);
    setSelectedBooking(null);
    setRescheduleOptions([]);
    setRescheduleError(null);
    setOptionSubmitting(null);
  };

  const handleApplyOption = async (option) => {
    if (!selectedBooking) return;
    setOptionSubmitting(option.start_time);
    setRescheduleError(null);
    try {
      const response = await fetch(`/api/bookings/${selectedBooking.id}/client_reschedule`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          start_time: option.start_time,
          end_time: option.end_time,
          staff_id: option.staff_id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update booking');
      }

      const updated = await response.json();
      setBookings(prev => prev.map(b => (b.id === updated.id ? updated : b)));
      closeRescheduleModal();
    } catch (err) {
      setRescheduleError('Unable to apply that slot. Please try another option.');
      console.error('Error applying reschedule option:', err);
    } finally {
      setOptionSubmitting(null);
    }
  };

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
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 animate-fade-in">
            {error}
          </div>
        )}
        {bookings.length === 0 ? (
          <p>You have no bookings yet.</p>
        ) : (
          <div className="grid gap-4">
            {bookings.map((booking) => (
              <Card key={booking.id} className="shadow-sm transition hover:shadow-lg animate-fade-in">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Booking #{booking.id}</CardTitle>
                    <p className="text-sm text-muted-foreground">{new Date(booking.start_time).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}</p>
                  </div>
                  <span className={`px-3 py-1 text-xs font-semibold rounded-full ${booking.status === 'cancelled' ? 'bg-red-100 text-red-700' : booking.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                    {booking.status}
                  </span>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="grid gap-1 sm:grid-cols-2">
                    <div>
                      <p className="text-muted-foreground">Starts</p>
                      <p className="font-medium">{new Date(booking.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Ends</p>
                      <p className="font-medium">{new Date(booking.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                    {booking.staff_id && (
                      <div>
                        <p className="text-muted-foreground">Staff</p>
                        <p className="font-medium">#{booking.staff_id}</p>
                      </div>
                    )}
                    {booking.pet_id && (
                      <div>
                        <p className="text-muted-foreground">Pet</p>
                        <p className="font-medium">#{booking.pet_id}</p>
                      </div>
                    )}
                  </div>
                  {booking.complaint_reason && (
                    <p className="text-sm text-muted-foreground border-l-2 border-primary pl-3">
                      {booking.complaint_reason}
                    </p>
                  )}
                  <div className="pt-3 flex flex-wrap gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={new Date(booking.start_time) <= new Date() || booking.status === 'cancelled'}
                      onClick={() => openRescheduleModal(booking)}
                    >
                      One-Click Reschedule
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
      {rescheduleModalOpen && selectedBooking && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 px-4 animate-fade-in">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Smart Rescheduling</h2>
                <p className="text-sm text-muted-foreground">We picked premium slots that respect your saved preferences.</p>
              </div>
              <Button size="sm" variant="ghost" onClick={closeRescheduleModal}>
                Close
              </Button>
            </div>
            <div className="mt-4 space-y-3">
              {rescheduleError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {rescheduleError}
                </div>
              )}
              {optionsLoading ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">🤖 AI is finding the best slots for you...</p>
                  {[...Array(3)].map((_, idx) => (
                    <div key={idx} className="h-20 rounded-xl border bg-muted/30 animate-pulse" />
                  ))}
                </div>
              ) : rescheduleOptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No perfect matches yet. Try again in a moment.</p>
              ) : (
                rescheduleOptions.map((option) => (
                  <div key={option.start_time} className="rounded-xl border p-4 shadow-sm animate-fade-in">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold">{new Date(option.start_time).toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground">
                          {option.staff_name ? option.staff_name : `Staff #${option.staff_id}`} · Pref match {(option.preference_match ?? 0).toFixed(2)}
                        </p>
                        {option.reason && (
                          <p className="text-xs text-muted-foreground mt-1">{option.reason}</p>
                        )}
                      </div>
                      <Button
                        size="sm"
                        className="animate-fade-in"
                        disabled={optionSubmitting === option.start_time}
                        onClick={() => handleApplyOption(option)}
                      >
                        {optionSubmitting === option.start_time ? 'Applying...' : 'Choose Slot'}
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </ProtectedRoute>
  );
}
