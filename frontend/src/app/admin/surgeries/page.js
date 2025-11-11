"use client";

import { useState, useEffect } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

export default function SurgeryManagementPage() {
  return (
    <AdminProtectedRoute>
      <SurgeryManagementContent />
    </AdminProtectedRoute>
  );
}

function SurgeryManagementContent() {
  const { token } = useAuth();
  const [surgeries, setSurgeries] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingSurgery, setEditingSurgery] = useState(null);

  // Filters
  const [filterDate, setFilterDate] = useState("");
  const [filterStaffId, setFilterStaffId] = useState("");
  const [filterPetId, setFilterPetId] = useState("");

  // Form state
  const [formData, setFormData] = useState({
    pet_id: "",
    staff_id: "",
    surgery_type: "",
    notes: "",
    start_time: "",
    end_time: "",
    status: "Scheduled",
  });

  const fetchSurgeries = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (filterDate) params.append("date", filterDate);
      if (filterStaffId) params.append("staff_id", filterStaffId);
      if (filterPetId) params.append("pet_id", filterPetId);

      const url = `/api/surgeries/?${params.toString()}`;
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch surgeries");
      }

      const data = await response.json();
      setSurgeries(data);
    } catch (err) {
      setError("Failed to fetch surgeries.");
      console.error("Error fetching surgeries:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSurgeries();
    }
  }, [token, filterDate, filterStaffId, filterPetId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      if (editingSurgery) {
        // Update existing surgery
        const updatePayload = {};
        Object.keys(formData).forEach((key) => {
          if (formData[key]) updatePayload[key] = formData[key];
        });

        const response = await fetch(`/api/surgeries/${editingSurgery.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(updatePayload),
        });

        if (!response.ok) {
          throw new Error("Failed to update surgery");
        }

        setEditingSurgery(null);
      } else {
        // Create new surgery
        const payload = {
          ...formData,
          pet_id: parseInt(formData.pet_id),
          staff_id: parseInt(formData.staff_id),
        };

        const response = await fetch("/api/surgeries/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || "Failed to create surgery");
        }
      }

      // Reset form
      setFormData({
        pet_id: "",
        staff_id: "",
        surgery_type: "",
        notes: "",
        start_time: "",
        end_time: "",
        status: "Scheduled",
      });

      // Refresh surgeries list
      fetchSurgeries();
    } catch (err) {
      setError(err.message);
      console.error("Error submitting surgery:", err);
    }
  };

  const handleEdit = (surgery) => {
    setEditingSurgery(surgery);
    setFormData({
      pet_id: surgery.pet_id.toString(),
      staff_id: surgery.staff_id.toString(),
      surgery_type: surgery.surgery_type,
      notes: surgery.notes || "",
      start_time: surgery.start_time.slice(0, 16), // Format for datetime-local
      end_time: surgery.end_time.slice(0, 16),
      status: surgery.status,
    });
  };

  const handleCancelEdit = () => {
    setEditingSurgery(null);
    setFormData({
      pet_id: "",
      staff_id: "",
      surgery_type: "",
      notes: "",
      start_time: "",
      end_time: "",
      status: "Scheduled",
    });
  };

  const handleDelete = async (surgeryId) => {
    if (!window.confirm("Are you sure you want to delete this surgery?")) {
      return;
    }

    try {
      const response = await fetch(`/api/surgeries/${surgeryId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete surgery");
      }

      fetchSurgeries();
    } catch (err) {
      setError("Failed to delete surgery.");
      console.error("Error deleting surgery:", err);
    }
  };

  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">
        Surgery Management
      </h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid gap-6">
        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="filterDate">Date</Label>
                <Input
                  id="filterDate"
                  type="date"
                  value={filterDate}
                  onChange={(e) => setFilterDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="filterStaff">Staff ID</Label>
                <Input
                  id="filterStaff"
                  type="number"
                  placeholder="Filter by staff ID"
                  value={filterStaffId}
                  onChange={(e) => setFilterStaffId(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="filterPet">Pet ID</Label>
                <Input
                  id="filterPet"
                  type="number"
                  placeholder="Filter by pet ID"
                  value={filterPetId}
                  onChange={(e) => setFilterPetId(e.target.value)}
                />
              </div>
            </div>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setFilterDate("");
                setFilterStaffId("");
                setFilterPetId("");
              }}
            >
              Clear Filters
            </Button>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Create/Edit Surgery Form */}
          <Card>
            <CardHeader>
              <CardTitle>{editingSurgery ? "Edit Surgery" : "Create Surgery"}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="pet_id">Pet ID *</Label>
                    <Input
                      id="pet_id"
                      type="number"
                      value={formData.pet_id}
                      onChange={(e) => setFormData({ ...formData, pet_id: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="staff_id">Staff ID *</Label>
                    <Input
                      id="staff_id"
                      type="number"
                      value={formData.staff_id}
                      onChange={(e) => setFormData({ ...formData, staff_id: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="surgery_type">Surgery Type *</Label>
                  <Input
                    id="surgery_type"
                    placeholder="e.g., Spay, Neuter, Orthopedic"
                    value={formData.surgery_type}
                    onChange={(e) => setFormData({ ...formData, surgery_type: e.target.value })}
                    required
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="start_time">Start Time *</Label>
                    <Input
                      id="start_time"
                      type="datetime-local"
                      value={formData.start_time}
                      onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end_time">End Time *</Label>
                    <Input
                      id="end_time"
                      type="datetime-local"
                      value={formData.end_time}
                      onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="status">Status *</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value) => setFormData({ ...formData, status: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Scheduled">Scheduled</SelectItem>
                      <SelectItem value="In-Progress">In-Progress</SelectItem>
                      <SelectItem value="Completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea
                    id="notes"
                    placeholder="Additional notes..."
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                  />
                </div>

                <div className="flex gap-2">
                  <Button type="submit" className="flex-1">
                    {editingSurgery ? "Update Surgery" : "Create Surgery"}
                  </Button>
                  {editingSurgery && (
                    <Button type="button" variant="outline" onClick={handleCancelEdit}>
                      Cancel
                    </Button>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Surgery List */}
          <Card>
            <CardHeader>
              <CardTitle>Surgeries</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading && <p>Loading...</p>}

              {!isLoading && surgeries.length === 0 && <p>No surgeries found.</p>}

              {!isLoading && surgeries.length > 0 && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Pet ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {surgeries.map((surgery) => (
                        <TableRow key={surgery.id}>
                          <TableCell>{surgery.surgery_type}</TableCell>
                          <TableCell>{surgery.pet_id}</TableCell>
                          <TableCell>{surgery.status}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleEdit(surgery)}
                              >
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleDelete(surgery.id)}
                              >
                                Delete
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
