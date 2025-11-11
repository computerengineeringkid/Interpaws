'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function PreferencesPage() {
  const { token } = useAuth();
  const [preferences, setPreferences] = useState({
    preferred_days: '',
    preferred_times: '',
    avoid_days: '',
    special_instructions: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        const response = await fetch('/api/preferences/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        if (response.ok) {
          const data = await response.json();
          if (data) {
            setPreferences({
              preferred_days: data.preferred_days || '',
              preferred_times: data.preferred_times || '',
              avoid_days: data.avoid_days || '',
              special_instructions: data.special_instructions || '',
            });
          }
        }
      } catch (error) {
        console.error('Error fetching preferences:', error);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchPreferences();
    }
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const response = await fetch('/api/preferences/me', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(preferences),
      });

      if (response.ok) {
        alert('Preferences saved successfully!');
      } else {
        alert('Failed to save preferences');
      }
    } catch (error) {
      console.error('Error saving preferences:', error);
      alert('Error saving preferences');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-8">
          <p>Loading your preferences...</p>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">My Preferences</h1>
        <Card>
          <CardHeader>
            <CardTitle>Booking Preferences</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="preferred_days">Preferred Days</Label>
                <Input
                  id="preferred_days"
                  value={preferences.preferred_days}
                  onChange={(e) => setPreferences({ ...preferences, preferred_days: e.target.value })}
                  placeholder="e.g., Monday, Wednesday, Friday"
                />
              </div>

              <div>
                <Label htmlFor="preferred_times">Preferred Times</Label>
                <Input
                  id="preferred_times"
                  value={preferences.preferred_times}
                  onChange={(e) => setPreferences({ ...preferences, preferred_times: e.target.value })}
                  placeholder="e.g., Morning, Afternoon"
                />
              </div>

              <div>
                <Label htmlFor="avoid_days">Days to Avoid</Label>
                <Input
                  id="avoid_days"
                  value={preferences.avoid_days}
                  onChange={(e) => setPreferences({ ...preferences, avoid_days: e.target.value })}
                  placeholder="e.g., Tuesday, Thursday"
                />
              </div>

              <div>
                <Label htmlFor="special_instructions">Special Instructions</Label>
                <Textarea
                  id="special_instructions"
                  value={preferences.special_instructions}
                  onChange={(e) => setPreferences({ ...preferences, special_instructions: e.target.value })}
                  placeholder="Any special notes or requirements..."
                  rows={4}
                />
              </div>

              <Button type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
