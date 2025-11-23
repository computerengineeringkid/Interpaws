"use client";

import React, { useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AuthContext } from "@/context/AuthContext";
import AIChat from "@/components/AIChat";
import { fetchWithAuth } from "@/utils/api";

const serviceOptions = [
  { value: "wellness exam", label: "Wellness Exam" },
  { value: "vaccination", label: "Vaccination" },
  { value: "urgent care", label: "Urgent Care" },
  { value: "surgery consult", label: "Surgery Consult" },
  { value: "dental cleaning", label: "Dental Cleaning" },
];

const BOOKINGS_BY_NAME_ENDPOINT = "/api/bookings/by-name"; // Avoid trailing slash to prevent 307 redirects

export default function ClientBookingForm({ complaint, setComplaint, aiChatRef }) {
  const { userRole, isAdmin, logout, clientToken, clientUser } = useContext(AuthContext);
  const router = useRouter();

  const [bookingMode, setBookingMode] = useState("ai");
  const [ownerName, setOwnerName] = useState(clientUser?.name || "");
  const [petName, setPetName] = useState("");
  const [petOptions, setPetOptions] = useState([]);
  const [petLoading, setPetLoading] = useState(false);
  const [newPetSpecies, setNewPetSpecies] = useState("Dog");
  const [newPetBreed, setNewPetBreed] = useState("");
  const [serviceType, setServiceType] = useState(serviceOptions[0].value);
  const [appointmentTime, setAppointmentTime] = useState("");
  const [status, setStatus] = useState(null);
  const [aiStartSignal, setAiStartSignal] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (clientUser?.name) {
      setOwnerName(clientUser.name);
    }
  }, [clientUser]);

  useEffect(() => {
    let active = true;
    if (!clientToken || !petName.trim()) {
      setPetOptions([]);
      return undefined;
    }

    const fetchPets = async () => {
      setPetLoading(true);
      try {
        const response = await fetchWithAuth(`/api/pets/me?name=${encodeURIComponent(petName)}`, {
          headers: {
            Authorization: `Bearer ${clientToken}`,
          },
        });
        if (!response.ok) throw new Error("Failed to search pets");
        const data = await response.json();
        if (active) setPetOptions(data || []);
      } catch (err) {
        if (active) setPetOptions([]);
      } finally {
        if (active) setPetLoading(false);
      }
    };

    fetchPets();
    return () => {
      active = false;
    };
  }, [petName, clientToken]);

  const handleCreatePet = async () => {
    if (!petName.trim()) return;
    setStatus(null);

    if (!clientToken) {
      setStatus({ type: "error", message: "Please log in to create a pet profile." });
      return;
    }

    try {
      const response = await fetchWithAuth("/api/pets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${clientToken}`,
        },
        body: JSON.stringify({
          name: petName,
          species: newPetSpecies,
          breed: newPetBreed
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unable to create pet" }));
        throw new Error(error.detail?.message || error.detail || "Unable to create pet");
      }

      const newPet = await response.json();
      setPetOptions(newPet ? [newPet] : []);
      setStatus({ type: "success", message: `Added ${newPet?.name || "your pet"} to your account.` });
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    }
  };

  const handleManualBooking = async () => {
    setStatus(null);
    if (!ownerName.trim() || !petName.trim() || !appointmentTime || !complaint.trim()) {
      setStatus({ type: "error", message: "Please provide owner name, pet name, complaint, and appointment time." });
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetchWithAuth(BOOKINGS_BY_NAME_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${clientToken}`,
        },
        body: JSON.stringify({
          owner_name: ownerName,
          pet_name: petName,
          service_type: serviceType,
          preferred_time: appointmentTime,
          complaint_reason: complaint,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Booking failed" }));
        throw new Error(error.detail || error.message || "Booking failed");
      }

      const booking = await response.json();
      const startTime = booking?.start_time ? new Date(booking.start_time).toLocaleString() : "the scheduled time";
      setStatus({ type: "success", message: `Appointment booked for ${petName} on ${startTime}.` });
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartChat = () => {
    setStatus(null);
    if (!ownerName.trim() || !petName.trim() || !complaint.trim()) {
      setStatus({ type: "error", message: "Please provide owner name, pet name, and a complaint before starting chat." });
      return;
    }
    setAiStartSignal((count) => count + 1);
  };

  const sharedFields = (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label htmlFor="ownerName">Owner Name</Label>
        <Input
          id="ownerName"
          value={ownerName}
          onChange={(e) => setOwnerName(e.target.value)}
          placeholder="Enter owner name"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="petName">Pet Name</Label>
        <Input
          id="petName"
          value={petName}
          onChange={(e) => setPetName(e.target.value)}
          placeholder="Search or add pet"
        />
        <div className="flex flex-wrap gap-2 pt-1">
          {petOptions.map((pet) => (
            <Button
              key={pet.id}
              type="button"
              size="sm"
              variant={petName.toLowerCase() === pet.name.toLowerCase() ? "secondary" : "outline"}
              onClick={() => setPetName(pet.name)}
            >
              {pet.name}{pet.species ? ` (${pet.species})` : ""}
            </Button>
          ))}
            {!petLoading && petName && petOptions.length === 0 && (
              <div className="mt-3 p-3 border rounded bg-zinc-50 dark:bg-zinc-800 space-y-3 w-full">
                <div className="space-y-2">
                  <Label htmlFor="newPetSpecies">Species</Label>
                  <Select value={newPetSpecies} onValueChange={setNewPetSpecies}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select species" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Dog">Dog</SelectItem>
                      <SelectItem value="Cat">Cat</SelectItem>
                      <SelectItem value="Bird">Bird</SelectItem>
                      <SelectItem value="Rabbit">Rabbit</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newPetBreed">Breed</Label>
                  <Input
                    id="newPetBreed"
                    value={newPetBreed}
                    onChange={(e) => setNewPetBreed(e.target.value)}
                    placeholder="Breed (optional)"
                  />
                </div>
                <Button type="button" size="sm" variant="outline" onClick={handleCreatePet} className="w-full">
                  Save &amp; Create Profile for &quot;{petName}&quot;
                </Button>
              </div>
            )}
        </div>
      </div>
    </div>
  );

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-lg">
      <CardHeader className="border-b bg-zinc-50 dark:bg-zinc-900">
        <CardTitle className="text-2xl text-center">Book an Appointment</CardTitle>
        <p className="text-center text-sm text-gray-600 mt-2">Use our AI assistant to quickly find the perfect appointment slot</p>
      </CardHeader>
      <CardContent className="p-0">
        {!clientToken && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-800 p-4 m-4" role="alert">
            <p className="font-bold">Could not validate credentials</p>
            <p>You are not logged in. You can get AI suggestions, but to create pets or book appointments, please{' '}
              <a href="/login" className="underline font-semibold hover:text-red-900">log in</a> or{' '}
              <a href="/register" className="underline font-semibold hover:text-red-900">register</a>.
            </p>
          </div>
        )}
        {isAdmin && (
          <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 m-4" role="alert">
            <p className="font-bold">Staff Account Detected</p>
            <p>You are logged in as a staff member. You cannot book client appointments from this form.</p>
            <Button variant="link" onClick={logout} className="p-0 h-auto font-bold underline">
              Log out
            </Button>
          </div>
        )}

        <div className="p-6 space-y-6">
          <div className="flex gap-2 items-center">
            <Button
              type="button"
              variant={bookingMode === "manual" ? "default" : "outline"}
              onClick={() => setBookingMode("manual")}
            >
              Manual
            </Button>
            <Button
              type="button"
              variant={bookingMode === "ai" ? "default" : "outline"}
              onClick={() => setBookingMode("ai")}
            >
              AI Assistant
            </Button>
          </div>

          {status && (
            <div
              className={`p-3 rounded-md ${status.type === "error" ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}
            >
              {status.message}
            </div>
          )}

          {sharedFields}

          {bookingMode === "manual" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="service">Service</Label>
                <Select value={serviceType} onValueChange={setServiceType}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Choose a service" />
                  </SelectTrigger>
                  <SelectContent>
                    {serviceOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="appointmentTime">Preferred Time</Label>
                  <Input
                    id="appointmentTime"
                    type="datetime-local"
                    value={appointmentTime}
                    onChange={(e) => setAppointmentTime(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="complaint">Complaint</Label>
                  <Textarea
                    id="complaint"
                    value={complaint}
                    onChange={(e) => setComplaint(e.target.value)}
                    placeholder="Describe the concern"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleManualBooking} disabled={isSubmitting}>
                  {isSubmitting ? "Booking..." : "Book Appointment"}
                </Button>
              </div>
            </div>
          )}

          {bookingMode === "ai" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="complaint">Complaint</Label>
                <Textarea
                  id="complaint"
                  value={complaint}
                  onChange={(e) => setComplaint(e.target.value)}
                  placeholder="Tell us what is happening with your pet"
                  className="min-h-[120px]"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => router.refresh()}>
                  Reset
                </Button>
                <Button onClick={handleStartChat} disabled={!petName || !ownerName}>
                  Start Chat
                </Button>
              </div>
              <AIChat
                ref={aiChatRef}
                token={clientToken}
                context={{ ownerName, petName, complaint }}
                startSignal={aiStartSignal}
                onBookingComplete={(message) => setStatus({ type: "success", message })}
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
