"use client";

import React from "react";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function AdminCalendar({ selectedDate, setSelectedDate }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin: Calendar View</CardTitle>
      </CardHeader>
      <CardContent>
        <Calendar 
          mode="single" 
          selected={selectedDate} 
          onSelect={setSelectedDate} 
        />
      </CardContent>
    </Card>
  );
}
