"use client";

import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export default function ClientPreferences() {
  const [details, setDetails] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async () => {
    if (!details.trim()) {
      alert("Please enter some notes about your pet.");
      return;
    }

    try {
      setIsSaving(true);
      const res = await fetch("/api/preferences/client/1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ details }),
      });

      if (res.ok) {
        alert("Preferences saved!");
        setDetails("");
      } else {
        const text = await res.text();
        console.error("Failed to save preferences:", text);
        alert("Could not save preferences. Please try again.");
      }
    } catch (e) {
      console.error(e);
      alert("An unexpected error occurred.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>My Pet Preferences</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col space-y-2">
          <Label htmlFor="preferences-details">Notes</Label>
          <Textarea
            id="preferences-details"
            placeholder="My cat is nervous around dogs, please allow extra time..."
            value={details}
            onChange={(e) => setDetails(e.target.value)}
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button onClick={handleSubmit} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Preferences"}
        </Button>
      </CardFooter>
    </Card>
  );
}
