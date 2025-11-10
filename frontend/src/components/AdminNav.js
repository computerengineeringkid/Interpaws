"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function AdminNav() {
  const pathname = usePathname();
  const { logout } = useAuth();

  const navItems = [
    { href: "/admin", label: "Dashboard" },
    { href: "/admin/staff", label: "Staff" },
    { href: "/admin/surgeries", label: "Surgeries" },
    { href: "/admin/medications", label: "Medications" },
  ];

  return (
    <nav className="bg-zinc-800 text-white">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h2 className="text-xl font-bold">Interpaws Admin</h2>
            <div className="flex gap-4">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded transition-colors ${
                    pathname === item.href
                      ? "bg-zinc-700 text-white"
                      : "text-zinc-300 hover:bg-zinc-700 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          <Button variant="outline" onClick={logout}>
            Logout
          </Button>
        </div>
      </div>
    </nav>
  );
}
