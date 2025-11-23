"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
  LayoutDashboard, 
  CalendarDays, 
  Users, 
  Stethoscope, 
  Pill, 
  Syringe, 
  LogOut,
  Settings
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AdminSidebar() {
  const pathname = usePathname();
  const { user, logout, isLoggedIn, isAdmin } = useAuth();

  // Hide sidebar if not logged in or not an admin
  if (!isLoggedIn || !isAdmin) {
    return null;
  }

  const navItems = [
    { href: "/admin/dashboard", label: "Overview", icon: LayoutDashboard },
    { href: "/admin/bookings", label: "Schedule", icon: CalendarDays },
    { href: "/admin/clients", label: "Clients & Patients", icon: Users },
    { href: "/admin/staff", label: "Staff Management", icon: Stethoscope },
    { href: "/admin/surgeries", label: "Surgeries", icon: Syringe },
    { href: "/admin/medications", label: "Inventory", icon: Pill },
  ];

  return (
    <aside className="hidden w-64 flex-col border-r bg-white dark:bg-zinc-950 md:flex">
      <div className="p-6">
        <div className="flex items-center gap-2 font-bold text-xl text-indigo-600 dark:text-indigo-400">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            🐾
          </div>
          Interpaws
        </div>
        <p className="text-xs text-zinc-500 mt-1 font-medium">Practice Manager</p>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <nav className="grid items-start px-4 text-sm font-medium gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                  isActive 
                    ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400" 
                    : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-50 dark:hover:bg-zinc-800"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto p-4 border-t">
        <div className="flex items-center justify-between mb-4 px-2">
            <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-zinc-100 flex items-center justify-center">
                    👨‍⚕️
                </div>
                <div className="text-xs">
                    <p className="font-medium">{user?.name || "Administrator"}</p>
                    <p className="text-zinc-500">{user?.role || "Staff"}</p>
                </div>
            </div>
        </div>
        <Button variant="outline" className="w-full justify-start gap-2 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={logout}>
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}