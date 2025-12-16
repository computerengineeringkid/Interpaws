"use client";

import { useState, useEffect } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { fetchWithAuth } from "@/utils/api";
import {
  DollarSign, Plus, Clock, Stethoscope, Syringe, Heart,
  Scissors, TestTube, AlertTriangle, Sparkles, Activity
} from "lucide-react";

const SERVICE_CATEGORIES = [
  { id: "checkup", label: "Checkup", icon: Stethoscope },
  { id: "vaccination", label: "Vaccination", icon: Syringe },
  { id: "surgery", label: "Surgery", icon: Heart },
  { id: "dental", label: "Dental", icon: Sparkles },
  { id: "grooming", label: "Grooming", icon: Scissors },
  { id: "emergency", label: "Emergency", icon: AlertTriangle },
  { id: "diagnostic", label: "Diagnostic", icon: TestTube },
  { id: "wellness", label: "Wellness", icon: Activity },
];

export default function ServicesPage() {
  return (
    <AdminProtectedRoute>
      <ServicesContent />
    </AdminProtectedRoute>
  );
}

function ServicesContent() {
  const { adminToken } = useAuth();
  const [services, setServices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingService, setEditingService] = useState(null);
  const [activeCategory, setActiveCategory] = useState("all");

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "checkup",
    duration_minutes: 30,
    base_price: "",
  });

  const fetchServices = async () => {
    if (!adminToken) return;
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeCategory !== "all") params.append("category", activeCategory);
      params.append("active_only", "false");

      const response = await fetchWithAuth(`/api/services?${params.toString()}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });

      if (response.ok) {
        setServices(await response.json());
      }
    } catch (err) {
      setError("Failed to fetch services");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) fetchServices();
  }, [adminToken, activeCategory]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const payload = {
        ...formData,
        duration_minutes: parseInt(formData.duration_minutes) || 30,
        base_price: Math.round(parseFloat(formData.base_price) * 100) || 0,
      };

      const url = editingService ? `/api/services/${editingService.id}` : "/api/services";
      const method = editingService ? "PUT" : "POST";

      const response = await fetchWithAuth(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to save service");

      resetForm();
      fetchServices();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (serviceId) => {
    if (!window.confirm("Are you sure you want to deactivate this service?")) return;
    try {
      await fetchWithAuth(`/api/services/${serviceId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      fetchServices();
    } catch (err) {
      setError("Failed to delete service");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      category: "checkup",
      duration_minutes: 30,
      base_price: "",
    });
    setEditingService(null);
    setShowModal(false);
  };

  const startEdit = (service) => {
    setEditingService(service);
    setFormData({
      name: service.name,
      description: service.description || "",
      category: service.category,
      duration_minutes: service.duration_minutes,
      base_price: (service.base_price / 100).toFixed(2),
    });
    setShowModal(true);
  };

  const formatCurrency = (cents) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  const getCategoryIcon = (category) => {
    const cat = SERVICE_CATEGORIES.find(c => c.id === category);
    return cat ? cat.icon : Stethoscope;
  };

  const filteredServices = activeCategory === "all"
    ? services
    : services.filter(s => s.category === activeCategory);

  // Calculate stats
  const totalServices = services.length;
  const activeServices = services.filter(s => s.is_active).length;
  const avgPrice = services.length > 0
    ? services.reduce((sum, s) => sum + s.base_price, 0) / services.length
    : 0;
  const avgDuration = services.length > 0
    ? services.reduce((sum, s) => sum + s.duration_minutes, 0) / services.length
    : 0;

  return (
    <main className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
            Services & Pricing
          </h1>
          <p className="text-zinc-500 mt-1">Manage clinic services and their pricing</p>
        </div>
        <Button onClick={() => setShowModal(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Service
        </Button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Stethoscope className="h-8 w-8 text-indigo-600" />
              <div>
                <p className="text-2xl font-bold">{totalServices}</p>
                <p className="text-xs text-zinc-500">Total Services</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-green-600" />
              <div>
                <p className="text-2xl font-bold text-green-600">{activeServices}</p>
                <p className="text-xs text-zinc-500">Active Services</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <DollarSign className="h-8 w-8 text-blue-600" />
              <div>
                <p className="text-2xl font-bold">{formatCurrency(avgPrice)}</p>
                <p className="text-xs text-zinc-500">Avg Price</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-orange-600" />
              <div>
                <p className="text-2xl font-bold">{Math.round(avgDuration)} min</p>
                <p className="text-xs text-zinc-500">Avg Duration</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <Button
          variant={activeCategory === "all" ? "default" : "outline"}
          onClick={() => setActiveCategory("all")}
        >
          All Categories
        </Button>
        {SERVICE_CATEGORIES.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={activeCategory === id ? "default" : "outline"}
            onClick={() => setActiveCategory(id)}
            className="gap-2 whitespace-nowrap"
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {/* Services Table */}
      <Card>
        <CardHeader>
          <CardTitle>Service Catalog</CardTitle>
          <CardDescription>
            {filteredServices.length} services {activeCategory !== "all" && `in ${activeCategory}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-center py-8">Loading services...</p>
          ) : filteredServices.length === 0 ? (
            <p className="text-center py-8 text-zinc-500">No services found</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredServices.map((service) => {
                  const CategoryIcon = getCategoryIcon(service.category);
                  return (
                    <TableRow key={service.id} className={!service.is_active ? "opacity-50" : ""}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                            <CategoryIcon className="h-5 w-5 text-indigo-600" />
                          </div>
                          <div>
                            <p className="font-medium">{service.name}</p>
                            {service.description && (
                              <p className="text-xs text-zinc-500 max-w-xs truncate">
                                {service.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {service.category}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Clock className="h-4 w-4 text-zinc-400" />
                          {service.duration_minutes} min
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-lg font-bold text-green-600">
                          {formatCurrency(service.base_price)}
                        </span>
                      </TableCell>
                      <TableCell>
                        {service.is_active ? (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600">
                            Inactive
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => startEdit(service)}>
                            Edit
                          </Button>
                          {service.is_active && (
                            <Button size="sm" variant="destructive" onClick={() => handleDelete(service.id)}>
                              Deactivate
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle>{editingService ? "Edit Service" : "Add New Service"}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Service Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Annual Wellness Exam"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Brief description of the service..."
                    rows={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category">Category *</Label>
                  <select
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full h-10 rounded-md border border-input bg-background px-3"
                    required
                  >
                    {SERVICE_CATEGORIES.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.label}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="duration">Duration (minutes) *</Label>
                    <Input
                      id="duration"
                      type="number"
                      min="5"
                      step="5"
                      value={formData.duration_minutes}
                      onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="price">Price ($) *</Label>
                    <Input
                      id="price"
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.base_price}
                      onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
                      placeholder="0.00"
                      required
                    />
                  </div>
                </div>

                <div className="flex gap-2 justify-end pt-4">
                  <Button type="button" variant="outline" onClick={resetForm}>
                    Cancel
                  </Button>
                  <Button type="submit">
                    {editingService ? "Update Service" : "Add Service"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}
