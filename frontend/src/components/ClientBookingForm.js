
"use client";

import React, { useState, useContext } from "react";
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
import { AuthContext } from "@/context/AuthContext";

export default function ClientBookingForm({ complaint, setComplaint }) {
  const { user, login } = useContext(AuthContext);
  const [petName, setPetName] = useState("");
  const [petId, setPetId] = useState("");
  const [service, setService] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const [error, setError] = useState(null);
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [bookingError, setBookingError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setSuggestions(null);
    setError(null);
    
    try {
      const requestBody = {
        complaint_text: complaint
      };
      
      const response = await fetch('/api/suggest_slots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        throw new Error('Failed to get AI suggestions');
      }
      
      const result = await response.json();
      setSuggestions(result);
    } catch (err) {
      setError(err.message || 'An error occurred while getting suggestions');
      console.error('Error getting suggestions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBookAppointment = async () => {
    setBookingError(null);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const requestBody = {
        start_time: startTime,
        end_time: endTime,
        pet_id: parseInt(petId),
        staff_id: parseInt(selectedStaff)
      };
      
      const response = await fetch('/api/bookings/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to book appointment');
      }
      
      const result = await response.json();
      alert('Appointment booked successfully!');
      // Optionally reset form or navigate
    } catch (err) {
      setBookingError(err.message || 'An error occurred while booking the appointment');
      console.error('Error booking appointment:', err);
    }
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
              <Label htmlFor="petId">Pet ID</Label>
              <Input
                id="petId"
                type="number"
                placeholder="123"
                value={petId}
                onChange={(e) => setPetId(e.target.value)}
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
      
      {isLoading && (
        <CardContent>
          <p className="text-center text-gray-600">Loading AI suggestions...</p>
        </CardContent>
      )}
      
      {error && !isLoading && (
        <CardContent className="border-t pt-4">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        </CardContent>
      )}
      
      {suggestions && !isLoading && (
        <CardContent className="border-t pt-4">
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-lg mb-2">AI Recommendation:</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{suggestions.generative_recommendation}</p>
            </div>
            
            <div>
              <h3 className="font-semibold text-lg mb-2">Suggested Staff:</h3>
              <ul className="space-y-2">
                {suggestions.suggested_staff.map((staff) => (
                  <li key={staff.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                    <span className="font-medium">{staff.name}</span>
                    <span className="text-gray-600">({staff.role})</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="border-t pt-4">
              <h3 className="font-semibold text-lg mb-2">Book Appointment</h3>
              <div className="grid w-full items-center gap-4">
                <div className="flex flex-col space-y-1.5">
                  <Label htmlFor="selectedStaff">Select Staff</Label>
                  <Select value={selectedStaff} onValueChange={setSelectedStaff}>
                    <SelectTrigger id="selectedStaff">
                      <SelectValue placeholder="Select a staff member" />
                    </SelectTrigger>
                    <SelectContent>
                      {suggestions.suggested_staff.map((staff) => (
                        <SelectItem key={staff.id} value={staff.id.toString()}>
                          {staff.name} ({staff.role})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col space-y-1.5">
                  <Label htmlFor="startTime">Start Time</Label>
                  <Input
                    id="startTime"
                    type="datetime-local"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                  />
                </div>
                <div className="flex flex-col space-y-1.5">
                  <Label htmlFor="endTime">End Time</Label>
                  <Input
                    id="endTime"
                    type="datetime-local"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                  />
                </div>
              </div>
              <Button 
                onClick={handleBookAppointment} 
                type="button" 
                className="mt-4"
                disabled={!petId || !selectedStaff || !startTime || !endTime}
              >
                Book Appointment
              </Button>
              {bookingError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mt-4">
                  {bookingError}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
