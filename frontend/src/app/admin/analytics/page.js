"use client";

import { useState, useEffect } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fetchWithAuth } from "@/utils/api";
import {
  BarChart3, Users, TrendingUp, TrendingDown, AlertTriangle,
  UserCheck, UserX, DollarSign, Calendar, Activity
} from "lucide-react";

export default function AnalyticsPage() {
  return (
    <AdminProtectedRoute>
      <AnalyticsContent />
    </AdminProtectedRoute>
  );
}

function AnalyticsContent() {
  const { adminToken } = useAuth();
  const [noShowRisk, setNoShowRisk] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchAnalytics = async () => {
    if (!adminToken) return;
    setIsLoading(true);
    try {
      const [noShowRes, engagementRes, revenueRes] = await Promise.all([
        fetchWithAuth("/api/admin/analytics/clients/no-show-risk", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
        fetchWithAuth("/api/admin/analytics/clients/engagement", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
        fetchWithAuth("/api/admin/analytics/revenue", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
      ]);

      if (noShowRes.ok) setNoShowRisk(await noShowRes.json());
      if (engagementRes.ok) setEngagement(await engagementRes.json());
      if (revenueRes.ok) setRevenue(await revenueRes.json());
    } catch (err) {
      console.error("Error fetching analytics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) fetchAnalytics();
  }, [adminToken]);

  const formatCurrency = (cents) => {
    if (!cents) return "$0.00";
    return `$${(cents / 100).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    if (!value && value !== 0) return "0%";
    return `${(value * 100).toFixed(1)}%`;
  };

  const getRiskBadge = (level) => {
    const colors = {
      high: "bg-red-100 text-red-800 border-red-200",
      medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
      low: "bg-green-100 text-green-800 border-green-200",
    };
    return colors[level] || colors.low;
  };

  return (
    <main className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
          Analytics Dashboard
        </h1>
        <p className="text-zinc-500 mt-1">Insights on client behavior, revenue, and clinic performance</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 border-b pb-4">
        {[
          { id: "overview", label: "Overview", icon: BarChart3 },
          { id: "no-show", label: "No-Show Risk", icon: AlertTriangle },
          { id: "engagement", label: "Client Engagement", icon: Users },
          { id: "revenue", label: "Revenue", icon: DollarSign },
        ].map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={activeTab === id ? "default" : "ghost"}
            onClick={() => setActiveTab(id)}
            className="gap-2"
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <Activity className="h-8 w-8 animate-spin mx-auto text-indigo-600" />
          <p className="mt-2 text-zinc-500">Loading analytics...</p>
        </div>
      ) : (
        <>
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-zinc-500">Active Clients</p>
                        <p className="text-3xl font-bold">{engagement?.active_clients || 0}</p>
                        <p className="text-xs text-zinc-400 mt-1">Last 90 days</p>
                      </div>
                      <UserCheck className="h-10 w-10 text-green-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-zinc-500">Overall No-Show Rate</p>
                        <p className="text-3xl font-bold text-yellow-600">
                          {formatPercent(noShowRisk?.overall_no_show_rate)}
                        </p>
                        <p className="text-xs text-zinc-400 mt-1">All time</p>
                      </div>
                      <AlertTriangle className="h-10 w-10 text-yellow-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-zinc-500">Revenue This Month</p>
                        <p className="text-3xl font-bold text-green-600">
                          {formatCurrency(revenue?.revenue_this_month)}
                        </p>
                        <p className="text-xs text-zinc-400 mt-1">
                          {revenue?.revenue_last_month > 0 && (
                            <>
                              {revenue.revenue_this_month > revenue.revenue_last_month ? (
                                <span className="text-green-600">
                                  +{formatPercent((revenue.revenue_this_month - revenue.revenue_last_month) / revenue.revenue_last_month)} vs last month
                                </span>
                              ) : (
                                <span className="text-red-600">
                                  {formatPercent((revenue.revenue_this_month - revenue.revenue_last_month) / revenue.revenue_last_month)} vs last month
                                </span>
                              )}
                            </>
                          )}
                        </p>
                      </div>
                      <DollarSign className="h-10 w-10 text-green-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-zinc-500">High Risk Clients</p>
                        <p className="text-3xl font-bold text-red-600">
                          {noShowRisk?.total_high_risk || 0}
                        </p>
                        <p className="text-xs text-zinc-400 mt-1">Need attention</p>
                      </div>
                      <UserX className="h-10 w-10 text-red-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Quick Insights */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Client Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">New clients this month</span>
                        <span className="font-bold text-green-600">
                          {engagement?.new_clients_this_month || 0}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Returning clients this month</span>
                        <span className="font-bold">
                          {engagement?.returning_clients_this_month || 0}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Inactive clients</span>
                        <span className="font-bold text-yellow-600">
                          {engagement?.inactive_clients || 0}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Avg visits per client</span>
                        <span className="font-bold">
                          {engagement?.average_visits_per_client?.toFixed(1) || 0}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Revenue by Category</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {revenue?.revenue_by_category && Object.keys(revenue.revenue_by_category).length > 0 ? (
                      <div className="space-y-3">
                        {Object.entries(revenue.revenue_by_category)
                          .sort((a, b) => b[1] - a[1])
                          .slice(0, 5)
                          .map(([category, amount]) => (
                            <div key={category} className="flex justify-between items-center">
                              <span className="text-sm capitalize">{category}</span>
                              <span className="font-bold">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <p className="text-zinc-500 text-sm">No revenue data available yet</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* No-Show Risk Tab */}
          {activeTab === "no-show" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="border-red-200 bg-red-50">
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <AlertTriangle className="h-8 w-8 text-red-600 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-red-600">{noShowRisk?.total_high_risk || 0}</p>
                      <p className="text-sm text-red-700">High Risk Clients</p>
                    </div>
                  </CardContent>
                </Card>
                <Card className="border-yellow-200 bg-yellow-50">
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <AlertTriangle className="h-8 w-8 text-yellow-600 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-yellow-600">{noShowRisk?.total_medium_risk || 0}</p>
                      <p className="text-sm text-yellow-700">Medium Risk Clients</p>
                    </div>
                  </CardContent>
                </Card>
                <Card className="border-indigo-200 bg-indigo-50">
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <BarChart3 className="h-8 w-8 text-indigo-600 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-indigo-600">
                        {formatPercent(noShowRisk?.overall_no_show_rate)}
                      </p>
                      <p className="text-sm text-indigo-700">Overall No-Show Rate</p>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* High Risk Clients Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                    High Risk Clients
                  </CardTitle>
                  <CardDescription>
                    Clients with high no-show or cancellation rates that need attention
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {noShowRisk?.high_risk_clients?.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Client</TableHead>
                          <TableHead>Pets</TableHead>
                          <TableHead>Total Appts</TableHead>
                          <TableHead>No-Shows</TableHead>
                          <TableHead>No-Show Rate</TableHead>
                          <TableHead>Cancel Rate</TableHead>
                          <TableHead>Risk</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {noShowRisk.high_risk_clients.map((client) => (
                          <TableRow key={client.id}>
                            <TableCell>
                              <div>
                                <p className="font-medium">{client.name}</p>
                                <p className="text-xs text-zinc-500">{client.email}</p>
                              </div>
                            </TableCell>
                            <TableCell>{client.pets_count}</TableCell>
                            <TableCell>{client.analytics?.total_appointments || 0}</TableCell>
                            <TableCell className="text-red-600 font-medium">
                              {client.analytics?.no_show_count || 0}
                            </TableCell>
                            <TableCell>
                              {formatPercent(client.analytics?.no_show_rate)}
                            </TableCell>
                            <TableCell>
                              {formatPercent(client.analytics?.cancellation_rate)}
                            </TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskBadge(client.analytics?.risk_level)}`}>
                                {client.analytics?.risk_level?.toUpperCase()}
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center py-8 text-zinc-500">No high risk clients</p>
                  )}
                </CardContent>
              </Card>

              {/* Medium Risk Clients */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-600" />
                    Medium Risk Clients
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {noShowRisk?.medium_risk_clients?.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Client</TableHead>
                          <TableHead>Total Appts</TableHead>
                          <TableHead>No-Show Rate</TableHead>
                          <TableHead>Cancel Rate</TableHead>
                          <TableHead>Risk</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {noShowRisk.medium_risk_clients.slice(0, 10).map((client) => (
                          <TableRow key={client.id}>
                            <TableCell>
                              <div>
                                <p className="font-medium">{client.name}</p>
                                <p className="text-xs text-zinc-500">{client.email}</p>
                              </div>
                            </TableCell>
                            <TableCell>{client.analytics?.total_appointments || 0}</TableCell>
                            <TableCell>{formatPercent(client.analytics?.no_show_rate)}</TableCell>
                            <TableCell>{formatPercent(client.analytics?.cancellation_rate)}</TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskBadge(client.analytics?.risk_level)}`}>
                                MEDIUM
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center py-8 text-zinc-500">No medium risk clients</p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Engagement Tab */}
          {activeTab === "engagement" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <UserCheck className="h-8 w-8 text-green-600 mb-2" />
                    <p className="text-3xl font-bold">{engagement?.active_clients || 0}</p>
                    <p className="text-sm text-zinc-500">Active Clients</p>
                    <p className="text-xs text-zinc-400">Visited in last 90 days</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <UserX className="h-8 w-8 text-yellow-600 mb-2" />
                    <p className="text-3xl font-bold text-yellow-600">{engagement?.inactive_clients || 0}</p>
                    <p className="text-sm text-zinc-500">Inactive Clients</p>
                    <p className="text-xs text-zinc-400">No visit in 90+ days</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <TrendingUp className="h-8 w-8 text-indigo-600 mb-2" />
                    <p className="text-3xl font-bold text-indigo-600">{engagement?.new_clients_this_month || 0}</p>
                    <p className="text-sm text-zinc-500">New This Month</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <Calendar className="h-8 w-8 text-blue-600 mb-2" />
                    <p className="text-3xl font-bold">{engagement?.average_visits_per_client?.toFixed(1) || 0}</p>
                    <p className="text-sm text-zinc-500">Avg Visits/Client</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Top Clients</CardTitle>
                  <CardDescription>Most frequent visitors</CardDescription>
                </CardHeader>
                <CardContent>
                  {engagement?.top_clients?.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Client</TableHead>
                          <TableHead>Pets</TableHead>
                          <TableHead>Total Visits</TableHead>
                          <TableHead>Last Visit</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {engagement.top_clients.map((client, index) => (
                          <TableRow key={client.id}>
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm">
                                  {index + 1}
                                </span>
                                <div>
                                  <p className="font-medium">{client.name}</p>
                                  <p className="text-xs text-zinc-500">{client.email}</p>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>{client.pets_count}</TableCell>
                            <TableCell className="font-medium">{client.analytics?.total_appointments || 0}</TableCell>
                            <TableCell>
                              {client.analytics?.last_visit_date
                                ? new Date(client.analytics.last_visit_date).toLocaleDateString()
                                : "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center py-8 text-zinc-500">No client data available</p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Revenue Tab */}
          {activeTab === "revenue" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <DollarSign className="h-8 w-8 text-green-600 mb-2" />
                    <p className="text-3xl font-bold text-green-600">{formatCurrency(revenue?.total_revenue)}</p>
                    <p className="text-sm text-zinc-500">Total Revenue</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <TrendingUp className="h-8 w-8 text-indigo-600 mb-2" />
                    <p className="text-3xl font-bold">{formatCurrency(revenue?.revenue_this_month)}</p>
                    <p className="text-sm text-zinc-500">This Month</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <TrendingDown className="h-8 w-8 text-zinc-400 mb-2" />
                    <p className="text-3xl font-bold text-zinc-600">{formatCurrency(revenue?.revenue_last_month)}</p>
                    <p className="text-sm text-zinc-500">Last Month</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <BarChart3 className="h-8 w-8 text-blue-600 mb-2" />
                    <p className="text-3xl font-bold">{formatCurrency(revenue?.average_booking_value)}</p>
                    <p className="text-sm text-zinc-500">Avg Booking Value</p>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Top Services by Revenue</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {revenue?.top_services?.length > 0 ? (
                      <div className="space-y-4">
                        {revenue.top_services.map((service, index) => (
                          <div key={service.name} className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-xs">
                                {index + 1}
                              </span>
                              <div>
                                <p className="font-medium">{service.name}</p>
                                <p className="text-xs text-zinc-500">{service.count} bookings</p>
                              </div>
                            </div>
                            <span className="font-bold text-green-600">{formatCurrency(service.revenue)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-zinc-500 text-sm">No service revenue data yet</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Revenue by Category</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {revenue?.revenue_by_category && Object.keys(revenue.revenue_by_category).length > 0 ? (
                      <div className="space-y-4">
                        {Object.entries(revenue.revenue_by_category)
                          .sort((a, b) => b[1] - a[1])
                          .map(([category, amount]) => {
                            const total = Object.values(revenue.revenue_by_category).reduce((a, b) => a + b, 0);
                            const percent = total > 0 ? (amount / total * 100).toFixed(0) : 0;
                            return (
                              <div key={category}>
                                <div className="flex justify-between mb-1">
                                  <span className="text-sm capitalize">{category}</span>
                                  <span className="font-medium">{formatCurrency(amount)}</span>
                                </div>
                                <div className="w-full h-2 bg-zinc-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-indigo-600 rounded-full"
                                    style={{ width: `${percent}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    ) : (
                      <p className="text-zinc-500 text-sm">No category revenue data yet</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
