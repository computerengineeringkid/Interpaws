import React from "react";
import AdminCalendar from "@/components/AdminCalendar";
import AdminBookingList from "@/components/AdminBookingList";

export default function AdminDashboardPage() {
  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">Admin Dashboard</h1>
      <div className="grid gap-6 md:grid-cols-2">
        <AdminCalendar />
        <AdminBookingList />
      </div>
    </main>
  );
}
