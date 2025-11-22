'use client';

import { useContext } from 'react';
import { useRouter } from 'next/navigation';
import { AuthContext } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';

export default function Navigation() {
  const { user, token, userRole, logout } = useContext(AuthContext);
  const router = useRouter();

  return (
    <nav className="border-b bg-white shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <h1 className="text-2xl font-bold text-indigo-600 cursor-pointer" onClick={() => router.push('/')}>
              🐾 Interpaws VPMS
            </h1>
            {token && userRole === 'client' && (
              <div className="hidden md:flex space-x-4">
                <Button variant="ghost" onClick={() => router.push('/')}>
                  Book Appointment
                </Button>
                <Button variant="ghost" onClick={() => router.push('/my-bookings')}>
                  My Bookings
                </Button>
                <Button variant="ghost" onClick={() => router.push('/preferences')}>
                  Preferences
                </Button>
              </div>
            )}
            {token && userRole === 'admin' && (
              <div className="hidden md:flex space-x-4">
                <Button variant="ghost" onClick={() => router.push('/admin/dashboard')}>
                  Dashboard
                </Button>
                <Button variant="ghost" onClick={() => router.push('/admin/staff')}>
                  Staff
                </Button>
                <Button variant="ghost" onClick={() => router.push('/admin/surgeries')}>
                  Surgeries
                </Button>
                <Button variant="ghost" onClick={() => router.push('/admin/medications')}>
                  Medications
                </Button>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-4">
            {token ? (
              <>
                <span className="text-sm text-gray-600">
                  {user?.name || user?.email}
                </span>
                <Button variant="outline" onClick={logout}>
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" onClick={() => router.push('/login')}>
                  Login
                </Button>
                <Button onClick={() => router.push('/register')}>
                  Register
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
