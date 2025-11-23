"use client";

import React from "react";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function AdminCalendar({ selectedDate, setSelectedDate }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="bg-zinc-50/50 dark:bg-zinc-900/50 border-b px-4 py-3">
        <CardTitle className="text-sm font-medium">Calendar</CardTitle>
      </CardHeader>
      <CardContent className="p-3">
        <div className="flex justify-center">
          <Calendar 
            mode="single" 
            selected={selectedDate} 
            onSelect={setSelectedDate}
            className="w-full scale-90 sm:scale-100"
          />
        </div>
      </CardContent>
    </Card>
  );
}
