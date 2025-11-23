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
import { parseErrorResponse } from "@/utils/api";

export default function StaffManagementPage() {
  return (
    <AdminProtectedRoute>
      <StaffManagementContent />
    </AdminProtectedRoute>
  );
}

function StaffManagementContent() {
  // FIX: Use adminToken instead of token
  const { adminToken } = useAuth();
  const [staff, setStaff] = useState([]);
  const [isLoading, setIsLoading] = useState(true); // Start as true to avoid flash of "No staff found"
  const [error, setError] = useState(null);
  const [editingStaff, setEditingStaff] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    role: "",
    skills_description: "",
  });

  const fetchStaff = async () => {
    if (!adminToken) {
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/staff/", {
        headers: {
          // FIX: Use adminToken in header
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch staff");
      }

      const data = await response.json();
      setStaff(data);
    } catch (err) {
      setError("Failed to fetch staff members.");
      console.error("Error fetching staff:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // FIX: Check for adminToken
    if (!adminToken) {
      setIsLoading(false);
      return;
    }
    
    fetchStaff();
  }, [adminToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      if (editingStaff) {
        // Update existing staff
        const updatePayload = {};
        if (formData.name) updatePayload.name = formData.name;
        if (formData.role) updatePayload.role = formData.role;
        if (formData.skills_description) updatePayload.skills_description = formData.skills_description;

        const response = await fetch(`/api/staff/${editingStaff.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            // FIX: Use adminToken
            Authorization: `Bearer ${adminToken}`,
          },
          body: JSON.stringify(updatePayload),
        });

        if (!response.ok) {
          throw new Error("Failed to update staff");
        }

        setEditingStaff(null);
      } else {
        // Create new staff
        const response = await fetch("/api/staff/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // FIX: Use adminToken
            Authorization: `Bearer ${adminToken}`,
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          const errData = await parseErrorResponse(response);
          throw new Error(errData.detail || "Failed to create staff");
        }
      }

      // Reset form
      setFormData({
        name: "",
        email: "",
        password: "",
        role: "",
        skills_description: "",
      });

      // Refresh staff list
      fetchStaff();
    } catch (err) {
      setError(err.message);
      console.error("Error submitting staff:", err);
    }
  };

  const handleEdit = (staffMember) => {
    setEditingStaff(staffMember);
    setFormData({
      name: staffMember.name,
      email: staffMember.email,
      password: "", // Don't populate password
      role: staffMember.role,
      skills_description: staffMember.skills_description || "",
    });
  };

  const handleCancelEdit = () => {
    setEditingStaff(null);
    setFormData({
      name: "",
      email: "",
      password: "",
      role: "",
      skills_description: "",
    });
  };

  const handleDelete = async (staffId) => {
    if (!window.confirm("Are you sure you want to delete this staff member?")) {
      return;
    }

    try {
      const response = await fetch(`/api/staff/${staffId}`, {
        method: "DELETE",
        headers: {
          // FIX: Use adminToken
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete staff");
      }

      fetchStaff();
    } catch (err) {
      setError("Failed to delete staff member.");
      console.error("Error deleting staff:", err);
    }
  };

  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">
        Staff Management
      </h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Create/Edit Staff Form */}
        <Card>
          <CardHeader>
            <CardTitle>{editingStaff ? "Edit Staff" : "Create Staff"}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              {!editingStaff && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                    />
                  </div>
                </>
              )}

              <div className="space-y-2">
                <Label htmlFor="role">Role *</Label>
                <Input
                  id="role"
                  placeholder="e.g., Veterinarian, Technician"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="skills">Skills Description</Label>
                <Textarea
                  id="skills"
                  placeholder="Describe skills and expertise..."
                  value={formData.skills_description}
                  onChange={(e) =>
                    setFormData({ ...formData, skills_description: e.target.value })
                  }
                  rows={4}
                />
              </div>

              <div className="flex gap-2">
                <Button type="submit" className="flex-1">
                  {editingStaff ? "Update Staff" : "Create Staff"}
                </Button>
                {editingStaff && (
                  <Button type="button" variant="outline" onClick={handleCancelEdit}>
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Staff List */}
        <Card>
          <CardHeader>
            <CardTitle>Staff Members</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading && <p>Loading...</p>}

            {!isLoading && staff.length === 0 && <p>No staff members found.</p>}

            {!isLoading && staff.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {staff.map((member) => (
                    <TableRow key={member.id}>
                      <TableCell>{member.name}</TableCell>
                      <TableCell>{member.role}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleEdit(member)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDelete(member.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}