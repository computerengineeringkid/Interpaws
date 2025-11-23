"use client";

import { useState, useEffect, useRef } from "react";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { parseErrorResponse } from "@/utils/api";

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
  const recognitionRef = useRef(null);
  const [listeningSurgeryId, setListeningSurgeryId] = useState(null);
  const [dictationStatus, setDictationStatus] = useState(null);
  const [dictationError, setDictationError] = useState(null);
  const [isDictationProcessing, setIsDictationProcessing] = useState(false);

  // Inventory check state
  const [inventoryCheck, setInventoryCheck] = useState([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);

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

  // Check inventory when surgery_type changes
  useEffect(() => {
    const checkInventory = async () => {
      if (!formData.surgery_type || !token) {
        setInventoryCheck([]);
        return;
      }

      setInventoryLoading(true);
      try {
        const response = await fetch(
          `/api/surgeries/check_inventory?surgery_type=${encodeURIComponent(formData.surgery_type)}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error("Failed to check inventory");
        }

        const data = await response.json();
        setInventoryCheck(data.items || []);
      } catch (err) {
        console.error("Error checking inventory:", err);
        setInventoryCheck([]);
      } finally {
        setInventoryLoading(false);
      }
    };

    checkInventory();
  }, [formData.surgery_type, token]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    if (!dictationStatus) return undefined;
    const timer = setTimeout(() => setDictationStatus(null), 6000);
    return () => clearTimeout(timer);
  }, [dictationStatus]);

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
          const errData = await parseErrorResponse(response);
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

  const handleDictateNotes = (surgeryId) => {
    if (typeof window === "undefined") return;
    if (!token) {
      setDictationError("You must be logged in to dictate notes.");
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setDictationError("Speech recognition is not available in this browser.");
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setListeningSurgeryId(surgeryId);
      setDictationStatus(null);
      setDictationError(null);
      setIsDictationProcessing(false);
    };

    recognition.onerror = (event) => {
      setListeningSurgeryId(null);
      const friendlyError =
        event.error === "not-allowed"
          ? "Microphone access was denied. Please allow access and try again."
          : "Unable to capture audio. Please try again.";
      setDictationError(friendlyError);
    };

    recognition.onend = () => {
      setListeningSurgeryId(null);
      recognitionRef.current = null;
    };

    recognition.onresult = async (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (!transcript) {
        setDictationError("No speech detected. Please try again.");
        return;
      }

      setIsDictationProcessing(true);
      try {
        const response = await fetch(`/api/surgeries/${surgeryId}/smart_notes`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ raw_transcript: transcript }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || "Failed to structure notes.");
        }

        const data = await response.json();
        setDictationStatus(`Notes updated for surgery #${data.surgery_id}.`);
        fetchSurgeries();
      } catch (dictationErr) {
        setDictationError(dictationErr.message || "Unable to update notes.");
      } finally {
        setIsDictationProcessing(false);
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
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

      {listeningSurgeryId && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-2 rounded mb-4">
          🎧 Listening for surgery #{listeningSurgeryId}...
        </div>
      )}

      {isDictationProcessing && (
        <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-2 rounded mb-4">
          ✨ Structuring notes with AI...
        </div>
      )}

      {dictationStatus && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-2 rounded mb-4">
          {dictationStatus}
        </div>
      )}

      {dictationError && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded mb-4 flex items-center justify-between gap-4">
          <span>{dictationError}</span>
          <Button variant="ghost" size="sm" onClick={() => setDictationError(null)}>
            Dismiss
          </Button>
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

                {/* Inventory Check Display */}
                {formData.surgery_type && (
                  <div className="space-y-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                    <h3 className="font-semibold text-sm">Required Inventory:</h3>
                    {inventoryLoading && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Checking inventory...
                      </p>
                    )}
                    {!inventoryLoading && inventoryCheck.length === 0 && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        No inventory requirements configured for this surgery type.
                      </p>
                    )}
                    {!inventoryLoading && inventoryCheck.length > 0 && (
                      <ul className="space-y-1">
                        {inventoryCheck.map((item, idx) => (
                          <li
                            key={idx}
                            className={`text-sm flex justify-between ${
                              item.status === "Low"
                                ? "text-red-600 dark:text-red-400 font-semibold"
                                : "text-green-600 dark:text-green-400"
                            }`}
                          >
                            <span>
                              {item.medication_name}:
                            </span>
                            <span>
                              {item.required_quantity} required / {item.stock_quantity} in stock
                              {item.status === "Low" && " ⚠️"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

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
                        <TableHead>Notes</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {surgeries.map((surgery) => {
                        const truncatedNotes = surgery.notes
                          ? `${surgery.notes.slice(0, 120)}${
                              surgery.notes.length > 120 ? "…" : ""
                            }`
                          : "—";

                        return (
                          <TableRow key={surgery.id}>
                            <TableCell>{surgery.surgery_type}</TableCell>
                            <TableCell>{surgery.pet_id}</TableCell>
                            <TableCell>{surgery.status}</TableCell>
                            <TableCell className="max-w-xs whitespace-pre-line text-sm text-zinc-600 dark:text-zinc-300">
                              {truncatedNotes}
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-wrap gap-2">
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => handleDictateNotes(surgery.id)}
                                  disabled={Boolean(listeningSurgeryId) || isDictationProcessing}
                                >
                                  🎤 Dictate Notes
                                </Button>
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
                        );
                      })}
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
