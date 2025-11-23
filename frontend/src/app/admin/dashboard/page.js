"use client";

import React, { useState, useEffect } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import AdminCalendar from "@/components/AdminCalendar";
import AdminBookingList from "@/components/AdminBookingList";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  X, 
  TrendingUp, 
  AlertCircle, 
  Clock, 
  CalendarCheck 
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";

export default function AdminDashboardPage() {
  return (
    <AdminProtectedRoute>
      <AdminDashboardContent />
    </AdminProtectedRoute>
  );
}

function AdminDashboardContent() {
  const { adminToken } = useAuth();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [cancellationSuggestions, setCancellationSuggestions] = useState(null);
  const [forecastItems, setForecastItems] = useState([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState(null);
  
  // Stats state
  const [todayBookings, setTodayBookings] = useState([]);
  const [todaySurgeries, setTodaySurgeries] = useState([]);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    if (!adminToken) {
      setForecastLoading(false);
      return;
    }

    const fetchForecast = async () => {
      setForecastLoading(true);
      setForecastError(null);
      try {
        const response = await fetch("/api/admin/inventory/forecast", {
          headers: { Authorization: `Bearer ${adminToken}` },
        });

        if (!response.ok) throw new Error("Failed to load forecast");
        const data = await response.json();
        setForecastItems(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
        setForecastError("Unable to load inventory forecast.");
      } finally {
        setForecastLoading(false);
      }
    };

    fetchForecast();
  }, [adminToken]);

  // Fetch today's bookings and surgeries for stats
  useEffect(() => {
    if (!adminToken) {
      setStatsLoading(false);
      return;
    }

    const fetchStats = async () => {
      setStatsLoading(true);
      try {
        const today = new Date().toISOString().split('T')[0];
        
        // Fetch bookings for today
        const bookingsResponse = await fetch(`/api/bookings/${today}`, {
          headers: { Authorization: `Bearer ${adminToken}` },
        });
        
        if (bookingsResponse.ok) {
          const bookingsData = await bookingsResponse.json();
          setTodayBookings(Array.isArray(bookingsData) ? bookingsData : []);
        }

        // Fetch surgeries for today
        const surgeriesResponse = await fetch(`/api/surgeries/?date=${today}`, {
          headers: { Authorization: `Bearer ${adminToken}` },
        });
        
        if (surgeriesResponse.ok) {
          const surgeriesData = await surgeriesResponse.json();
          setTodaySurgeries(Array.isArray(surgeriesData) ? surgeriesData : []);
        }
      } catch (err) {
        console.error("Error fetching stats:", err);
      } finally {
        setStatsLoading(false);
      }
    };

    fetchStats();
  }, [adminToken]);

  // Count low stock items for the stats card
  const lowStockCount = forecastItems.filter(i => i.days_remaining < 7).length;
  
  // Calculate stats
  const pendingBookings = todayBookings.filter(b => b.status === 'pending').length;
  const nextSurgery = todaySurgeries
    .filter(s => new Date(s.start_time) > new Date())
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0];
  
  // Calculate revenue estimate (basic calculation based on bookings)
  const estimatedRevenue = todayBookings.reduce((sum, booking) => {
    // Rough estimate: $100 per booking
    return sum + 100;
  }, 0);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">Dashboard</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Overview of your clinic's daily operations.</p>
        </div>
        <div className="flex items-center gap-2">
            <Button>+ New Appointment</Button>
        </div>
      </div>

      {/* KPI Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard 
          title="Appointments Today" 
          value={statsLoading ? "..." : todayBookings.length.toString()} 
          icon={CalendarCheck} 
          description={pendingBookings > 0 ? `${pendingBookings} pending confirmation` : "All confirmed"}
        />
        <StatsCard 
          title="Surgery Schedule" 
          value={statsLoading ? "..." : todaySurgeries.length.toString()} 
          icon={Clock} 
          description={
            nextSurgery 
              ? `Next: ${nextSurgery.surgery_type || 'Surgery'} at ${new Date(nextSurgery.start_time).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'})}`
              : todaySurgeries.length > 0 ? "All surgeries completed" : "No surgeries scheduled"
          }
        />
        <StatsCard 
          title="Low Stock Alerts" 
          value={forecastLoading ? "..." : lowStockCount.toString()} 
          icon={AlertCircle} 
          description="Items < 7 days remaining"
          trend={lowStockCount > 0 ? "negative" : undefined}
        />
        <StatsCard 
          title="Revenue Est." 
          value={statsLoading ? "..." : `$${estimatedRevenue.toLocaleString()}`} 
          icon={TrendingUp} 
          description={todayBookings.length > 0 ? `From ${todayBookings.length} appointments` : "No appointments today"}
          trend="positive"
        />
      </div>
      
      {/* Cancellation Suggestions Banner */}
      {cancellationSuggestions && cancellationSuggestions.suggestions.length > 0 && (
        <Card className="border-l-4 border-l-blue-500 bg-blue-50/50 dark:bg-blue-950/20 shadow-sm">
          <CardHeader className="pb-2 pt-4">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-blue-900 dark:text-blue-100 flex items-center gap-2 text-base">
                  <Clock className="h-4 w-4" />
                  Cancellation Opportunity Found
                </CardTitle>
                <CardDescription className="text-blue-700 dark:text-blue-300 mt-1">
                  A slot opened at <span className="font-bold">{new Date(cancellationSuggestions.cancelled_slot_time).toLocaleTimeString([], {hour:'numeric', minute:'2-digit'})}</span>. 
                  Our AI found {cancellationSuggestions.suggestions.length} clients who prefer earlier times.
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-blue-700 hover:bg-blue-100"
                onClick={() => setCancellationSuggestions(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 mt-2 md:grid-cols-3">
              {cancellationSuggestions.suggestions.map((suggestion) => (
                <div key={suggestion.current_booking_id} className="bg-white p-3 rounded-md border border-blue-100 shadow-sm flex flex-col gap-2">
                    <div className="flex justify-between items-start">
                        <span className="font-semibold text-sm">{suggestion.client_name}</span>
                        <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                            {Math.round(suggestion.match_score * 100)}% match
                        </span>
                    </div>
                    <p className="text-xs text-zinc-500 line-clamp-2">{suggestion.reason}</p>
                    <Button size="sm" variant="secondary" className="w-full mt-auto h-7 text-xs">Contact</Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-7">
        
        {/* Left Col: Calendar & Inventory (Narrower) */}
        <div className="lg:col-span-2 space-y-6">
            <AdminCalendar selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
            
            <Card className="overflow-hidden">
                <CardHeader className="bg-zinc-50/50 border-b px-4 py-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <PillIcon className="h-4 w-4 text-zinc-500" /> Inventory Health
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {forecastLoading ? (
                        <div className="p-4 text-sm text-zinc-500">Analyzing usage...</div>
                    ) : (
                        <Table>
                            <TableBody>
                                {forecastItems.slice(0, 5).map((item, i) => (
                                    <TableRow key={i}>
                                        <TableCell className="py-2 text-xs font-medium">{item.medication_name}</TableCell>
                                        <TableCell className="py-2 text-xs text-right">
                                            <span className={item.days_remaining < 7 ? "text-red-600 font-bold" : "text-zinc-500"}>
                                                {Number(item.days_remaining).toFixed(0)} days
                                            </span>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {forecastItems.length === 0 && (
                                    <TableRow><TableCell colSpan={2} className="text-center text-xs text-zinc-500 h-24">Inventory levels healthy</TableCell></TableRow>
                                )}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>

        {/* Right Col: Bookings List (Wider) */}
        <div className="lg:col-span-5">
            <Card className="h-full border-none shadow-none bg-transparent">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Schedule for {selectedDate.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric'})}</h2>
                </div>
                <AdminBookingList 
                    selectedDate={selectedDate}
                />
            </Card>
        </div>
      </div>
    </div>
  );
}

function StatsCard({ title, value, icon: Icon, description, trend }) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-zinc-500">{title}</CardTitle>
                <Icon className={`h-4 w-4 ${trend === 'negative' ? 'text-red-500' : 'text-zinc-500'}`} />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
                <p className="text-xs text-zinc-500 mt-1">
                    {description}
                </p>
            </CardContent>
        </Card>
    )
}

function PillIcon(props) {
    return (
      <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/></svg>
    )
}