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
  // CRITICAL FIX: Use adminToken
  const { adminToken } = useAuth();
  const [surgeries, setSurgeries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingSurgery, setEditingSurgery] = useState(null);
  const recognitionRef = useRef(null);
  const [listeningSurgeryId, setListeningSurgeryId] = useState(null);
  const [dictationStatus, setDictationStatus] = useState(null);
  const [dictationError, setDictationError] = useState(null);
  const [isDictationProcessing, setIsDictationProcessing] = useState(false);

  const [inventoryCheck, setInventoryCheck] = useState([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);

  const [filterDate, setFilterDate] = useState("");
  const [filterStaffId, setFilterStaffId] = useState("");
  const [filterPetId, setFilterPetId] = useState("");

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
    if (!adminToken) return;
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
          // CRITICAL FIX: Use adminToken
          Authorization: `Bearer ${adminToken}`,
        },
      });

      if (!response.ok) throw new Error("Failed to fetch surgeries");

      const data = await response.json();
      setSurgeries(data);
    } catch (err) {
      setError("Failed to fetch surgeries.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) fetchSurgeries();
  }, [adminToken, filterDate, filterStaffId, filterPetId]);

  useEffect(() => {
    const checkInventory = async () => {
      if (!formData.surgery_type || !adminToken) {
        setInventoryCheck([]);
        return;
      }

      setInventoryLoading(true);
      try {
        const response = await fetch(
          `/api/surgeries/check_inventory?surgery_type=${encodeURIComponent(formData.surgery_type)}`,
          {
            // CRITICAL FIX: Use adminToken
            headers: { Authorization: `Bearer ${adminToken}` }, 
          }
        );

        if (!response.ok) throw new Error("Failed to check inventory");
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
  }, [formData.surgery_type, adminToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const headers = {
        "Content-Type": "application/json",
        // CRITICAL FIX: Use adminToken
        Authorization: `Bearer ${adminToken}`, 
      };

      if (editingSurgery) {
        const updatePayload = {};
        Object.keys(formData).forEach((key) => {
          if (formData[key]) updatePayload[key] = formData[key];
        });

        const response = await fetch(`/api/surgeries/${editingSurgery.id}`, {
          method: "PUT",
          headers,
          body: JSON.stringify(updatePayload),
        });

        if (!response.ok) throw new Error("Failed to update surgery");
        setEditingSurgery(null);
      } else {
        const payload = {
          ...formData,
          pet_id: parseInt(formData.pet_id),
          staff_id: parseInt(formData.staff_id),
        };

        const response = await fetch("/api/surgeries/", {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errData = await parseErrorResponse(response);
          throw new Error(errData.detail || "Failed to create surgery");
        }
      }

      setFormData({ pet_id: "", staff_id: "", surgery_type: "", notes: "", start_time: "", end_time: "", status: "Scheduled" });
      fetchSurgeries();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (surgery) => {
    setEditingSurgery(surgery);
    setFormData({
      pet_id: surgery.pet_id.toString(),
      staff_id: surgery.staff_id.toString(),
      surgery_type: surgery.surgery_type,
      notes: surgery.notes || "",
      start_time: surgery.start_time.slice(0, 16), 
      end_time: surgery.end_time.slice(0, 16),
      status: surgery.status,
    });
  };
  
  const handleCancelEdit = () => {
    setEditingSurgery(null);
    setFormData({ pet_id: "", staff_id: "", surgery_type: "", notes: "", start_time: "", end_time: "", status: "Scheduled" });
  };

  const handleDelete = async (surgeryId) => {
    if (!window.confirm("Are you sure you want to delete this surgery?")) return;
    try {
      const response = await fetch(`/api/surgeries/${surgeryId}`, {
        method: "DELETE",
        // CRITICAL FIX: Use adminToken
        headers: { Authorization: `Bearer ${adminToken}` }, 
      });
      if (!response.ok) throw new Error("Failed to delete surgery");
      fetchSurgeries();
    } catch (err) {
      setError("Failed to delete surgery.");
    }
  };

  const handleDictateNotes = (surgeryId) => {
     if (typeof window === "undefined") return;
     const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
     if (!SpeechRecognition) return;
     
     const recognition = new SpeechRecognition();
     recognition.onresult = async (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (!transcript) return;

      setIsDictationProcessing(true);
      try {
        const response = await fetch(`/api/surgeries/${surgeryId}/smart_notes`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // CRITICAL FIX: Use adminToken
            Authorization: `Bearer ${adminToken}`, 
          },
          body: JSON.stringify({ raw_transcript: transcript }),
        });

        if (!response.ok) throw new Error("Failed to structure notes.");
        const data = await response.json();
        setDictationStatus(`Notes updated for surgery #${data.surgery_id}.`);
        fetchSurgeries();
      } catch (dictationErr) {
        setDictationError(dictationErr.message);
      } finally {
        setIsDictationProcessing(false);
      }
    };
    recognition.start();
  };

  return (
    <main className="container mx-auto py-12 px-4">
      <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">Surgery Management</h1>
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      
      <div className="grid gap-6">
        <Card>
            <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
            <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-2"><Label>Date</Label><Input type="date" value={filterDate} onChange={(e)=>setFilterDate(e.target.value)} /></div>
                    <div className="space-y-2"><Label>Staff ID</Label><Input value={filterStaffId} onChange={(e)=>setFilterStaffId(e.target.value)} /></div>
                    <div className="space-y-2"><Label>Pet ID</Label><Input value={filterPetId} onChange={(e)=>setFilterPetId(e.target.value)} /></div>
                </div>
                <Button variant="outline" className="mt-4" onClick={() => { setFilterDate(""); setFilterStaffId(""); setFilterPetId(""); }}>Clear Filters</Button>
            </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
             <Card>
                <CardHeader><CardTitle>{editingSurgery ? "Edit Surgery" : "Create Surgery"}</CardTitle></CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2"><Label>Pet ID *</Label><Input value={formData.pet_id} onChange={(e)=>setFormData({...formData, pet_id: e.target.value})} required /></div>
                            <div className="space-y-2"><Label>Staff ID *</Label><Input value={formData.staff_id} onChange={(e)=>setFormData({...formData, staff_id: e.target.value})} required /></div>
                        </div>
                        <div className="space-y-2"><Label>Surgery Type *</Label><Input value={formData.surgery_type} onChange={(e)=>setFormData({...formData, surgery_type: e.target.value})} required /></div>
                        
                        {formData.surgery_type && (
                             <div className="space-y-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                                <h3 className="font-semibold text-sm">Required Inventory:</h3>
                                {inventoryLoading && <p className="text-sm text-gray-500">Checking...</p>}
                                {!inventoryLoading && inventoryCheck.map((item, idx) => (
                                    <div key={idx} className="text-sm flex justify-between"><span>{item.medication_name}</span><span>{item.stock_quantity} / {item.required_quantity}</span></div>
                                ))}
                             </div>
                        )}

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2"><Label>Start Time</Label><Input type="datetime-local" value={formData.start_time} onChange={(e)=>setFormData({...formData, start_time: e.target.value})} required /></div>
                            <div className="space-y-2"><Label>End Time</Label><Input type="datetime-local" value={formData.end_time} onChange={(e)=>setFormData({...formData, end_time: e.target.value})} required /></div>
                        </div>
                        <div className="space-y-2">
                             <Label>Status</Label>
                             <Select value={formData.status} onValueChange={(val)=>setFormData({...formData, status: val})}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="Scheduled">Scheduled</SelectItem>
                                    <SelectItem value="In-Progress">In-Progress</SelectItem>
                                    <SelectItem value="Completed">Completed</SelectItem>
                                </SelectContent>
                             </Select>
                        </div>
                        <div className="space-y-2"><Label>Notes</Label><Textarea value={formData.notes} onChange={(e)=>setFormData({...formData, notes: e.target.value})} /></div>
                        <div className="flex gap-2">
                            <Button type="submit" className="flex-1">{editingSurgery ? "Update" : "Create"}</Button>
                            {editingSurgery && <Button type="button" variant="outline" onClick={handleCancelEdit}>Cancel</Button>}
                        </div>
                    </form>
                </CardContent>
             </Card>
             <Card>
                <CardHeader><CardTitle>Surgeries</CardTitle></CardHeader>
                <CardContent>
                    {isLoading ? <p>Loading...</p> : (
                        <div className="space-y-2">
                            {surgeries.map(s => (
                                <div key={s.id} className="flex justify-between p-2 border rounded">
                                    <div><p className="font-bold">{s.surgery_type}</p><p className="text-sm">{s.status}</p></div>
                                    <div className="flex gap-2">
                                        <Button size="sm" variant="outline" onClick={()=>handleEdit(s)}>Edit</Button>
                                        <Button size="sm" variant="destructive" onClick={()=>handleDelete(s.id)}>Del</Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
             </Card>
        </div>
      </div>
    </main>
  );
}