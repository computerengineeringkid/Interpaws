"use client";

import React from "react";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function AdminCalendar() {
  const [date, setDate] = React.useState(new Date());

  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin: Calendar View</CardTitle>
      </CardHeader>
      <CardContent>
        <Calendar mode="single" selected={date} onSelect={setDate} />
      </CardContent>
    </Card>
  );
}
