"use client";

import AdminNav from "@/components/AdminNav";

export default function AdminLayout({ children }) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AdminNav />
      {children}
    </div>
  );
}
