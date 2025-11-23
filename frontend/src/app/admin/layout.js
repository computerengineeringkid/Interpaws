"use client";

import AdminSidebar from "@/components/AdminSidebar";

export default function AdminLayout({ children }) {
  return (
    <div className="flex h-screen w-full bg-zinc-50/50 dark:bg-zinc-900">
      <AdminSidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Optional Top Header for Mobile Menu triggers or Breadcrumbs could go here */}
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}