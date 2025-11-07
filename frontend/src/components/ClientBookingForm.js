
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
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";

export default function ClientBookingForm() {
  const [petName, setPetName] = useState("");
  const [service, setService] = useState("");
  const [complaint, setComplaint] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date());

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log({ petName, service, complaint, selectedDate });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Client: Book an Appointment</CardTitle>
      </CardHeader>
      <CardContent>
        <form>
          <div className="grid w-full items-center gap-4">
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="petName">Pet Name</Label>
              <Input
                id="petName"
                placeholder="Fido"
                value={petName}
                onChange={(e) => setPetName(e.target.value)}
              />
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="service">Service</Label>
              <Select
                value={service}
                onValueChange={setService}
              >
                <SelectTrigger id="service">
                  <SelectValue placeholder="Select a service" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="wellness">Wellness Check</SelectItem>
                  <SelectItem value="vaccination">Vaccination</SelectItem>
                  <SelectItem value="grooming">Grooming</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="complaint">Reason for Visit (e.g., 'limping on front paw')</Label>
              <Textarea
                id="complaint"
                placeholder="Tell us what's wrong..."
                value={complaint}
                onChange={(e) => setComplaint(e.target.value)}
              />
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="date">Select a Date</Label>
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={setSelectedDate}
                className="rounded-md border"
              />
            </div>
          </div>
        </form>
      </CardContent>
      <CardFooter>
        <Button onClick={handleSubmit} type="button">Get AI Suggestions</Button>
      </CardFooter>
    </Card>
  );
}
