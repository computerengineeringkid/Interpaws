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

export default function MedicationManagementPage() {
  return (
    <AdminProtectedRoute>
      <MedicationManagementContent />
    </AdminProtectedRoute>
  );
}

function MedicationManagementContent() {
  const { token } = useAuth();
  const [medications, setMedications] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingMedication, setEditingMedication] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    stock_quantity: "",
    unit: "",
  });

  const fetchMedications = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/medications/", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch medications");
      }

      const data = await response.json();
      setMedications(data);
    } catch (err) {
      setError("Failed to fetch medications.");
      console.error("Error fetching medications:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchMedications();
    }
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      if (editingMedication) {
        // Update existing medication
        const updatePayload = {};
        Object.keys(formData).forEach((key) => {
          if (formData[key] !== "") {
            updatePayload[key] = key === "stock_quantity" ? parseInt(formData[key]) : formData[key];
          }
        });

        const response = await fetch(`http://localhost:8000/medications/${editingMedication.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(updatePayload),
        });

        if (!response.ok) {
          throw new Error("Failed to update medication");
        }

        setEditingMedication(null);
      } else {
        // Create new medication
        const payload = {
          ...formData,
          stock_quantity: parseInt(formData.stock_quantity) || 0,
        };

        const response = await fetch("http://localhost:8000/medications/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || "Failed to create medication");
        }
      }

      // Reset form
      setFormData({
        name: "",
        description: "",
        stock_quantity: "",
        unit: "",
      });

      // Refresh medications list
      fetchMedications();
    } catch (err) {
      setError(err.message);
      console.error("Error submitting medication:", err);
    }
  };

  const handleEdit = (medication) => {
    setEditingMedication(medication);
    setFormData({
      name: medication.name,
      description: medication.description || "",
      stock_quantity: medication.stock_quantity.toString(),
      unit: medication.unit,
    });
  };

  const handleCancelEdit = () => {
    setEditingMedication(null);
    setFormData({
      name: "",
      description: "",
      stock_quantity: "",
      unit: "",
    });
  };

  const handleDelete = async (medicationId) => {
    if (!window.confirm("Are you sure you want to delete this medication?")) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/medications/${medicationId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete medication");
      }

      fetchMedications();
    } catch (err) {
      setError("Failed to delete medication.");
      console.error("Error deleting medication:", err);
    }
  };

  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">
        Medication Inventory
      </h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Create/Edit Medication Form */}
        <Card>
          <CardHeader>
            <CardTitle>
              {editingMedication ? "Edit Medication" : "Add Medication"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Medication Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Amoxicillin"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Medication description..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="stock_quantity">Stock Quantity *</Label>
                  <Input
                    id="stock_quantity"
                    type="number"
                    min="0"
                    value={formData.stock_quantity}
                    onChange={(e) =>
                      setFormData({ ...formData, stock_quantity: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit">Unit *</Label>
                  <Input
                    id="unit"
                    placeholder="e.g., tablets, ml, mg"
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button type="submit" className="flex-1">
                  {editingMedication ? "Update Medication" : "Add Medication"}
                </Button>
                {editingMedication && (
                  <Button type="button" variant="outline" onClick={handleCancelEdit}>
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Medication List */}
        <Card>
          <CardHeader>
            <CardTitle>Inventory</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading && <p>Loading...</p>}

            {!isLoading && medications.length === 0 && <p>No medications in inventory.</p>}

            {!isLoading && medications.length > 0 && (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Stock</TableHead>
                      <TableHead>Unit</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {medications.map((medication) => (
                      <TableRow key={medication.id}>
                        <TableCell className="font-medium">{medication.name}</TableCell>
                        <TableCell>
                          <span
                            className={
                              medication.stock_quantity < 10
                                ? "text-red-600 font-semibold"
                                : ""
                            }
                          >
                            {medication.stock_quantity}
                          </span>
                        </TableCell>
                        <TableCell>{medication.unit}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEdit(medication)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDelete(medication.id)}
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
    </main>
  );
}
