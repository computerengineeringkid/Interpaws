"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export default function PreferencesPage() {
  const { isAuthenticated, token, loading: authLoading, logout } = useAuth();
  const [preferences, setPreferences] = useState([]);
  const [newPreference, setNewPreference] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchPreferences();
    }
  }, [isAuthenticated, token]);

  const fetchPreferences = async () => {
    try {
      const response = await fetch("/api/preferences/me", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          logout();
          return;
        }
        throw new Error("Failed to fetch preferences");
      }

      const data = await response.json();
      setPreferences(data);
    } catch (err) {
      setError(err.message || "An error occurred while fetching preferences");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      const response = await fetch("/api/preferences/me", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          details: newPreference,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          logout();
          return;
        }
        throw new Error("Failed to save preference");
      }

      const data = await response.json();
      setPreferences([data, ...preferences]);
      setNewPreference("");
      setSuccess("Preference saved successfully!");
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.message || "An error occurred while saving preference");
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">My Preferences</h1>
          <div className="space-x-2">
            <Button onClick={() => router.push("/my-bookings")} variant="outline">
              My Bookings
            </Button>
            <Button onClick={logout} variant="outline">
              Logout
            </Button>
          </div>
        </div>

        {/* Add New Preference Form */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Add New Preference</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="preference">
                  Tell us about your pet's needs, preferred times, or special requirements
                </Label>
                <Textarea
                  id="preference"
                  placeholder="Example: My dog is afraid of loud noises and prefers morning appointments. She also needs a vet experienced with large breeds."
                  value={newPreference}
                  onChange={(e) => setNewPreference(e.target.value)}
                  rows={5}
                  required
                />
              </div>

              {error && (
                <div className="text-red-500 text-sm p-2 bg-red-50 rounded">
                  {error}
                </div>
              )}

              {success && (
                <div className="text-green-500 text-sm p-2 bg-green-50 rounded">
                  {success}
                </div>
              )}

              <Button type="submit" disabled={submitting || !newPreference.trim()}>
                {submitting ? "Saving..." : "Save Preference"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Existing Preferences */}
        <Card>
          <CardHeader>
            <CardTitle>Saved Preferences</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-center py-4">Loading preferences...</p>
            ) : preferences.length === 0 ? (
              <p className="text-center py-8 text-gray-500">
                No preferences saved yet. Add one above to help us serve you better!
              </p>
            ) : (
              <div className="space-y-4">
                {preferences.map((pref) => (
                  <Card key={pref.id} className="bg-gray-50">
                    <CardContent className="pt-6">
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {pref.details}
                      </p>
                    </CardContent>
                    <CardFooter className="text-xs text-gray-500">
                      Preference ID: {pref.id}
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
