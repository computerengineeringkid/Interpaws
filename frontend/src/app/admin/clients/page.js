"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import AdminProtectedRoute from "@/components/AdminProtectedRoute";

export default function ClientLookupPage() {
  // FIX: Use adminToken
  const { adminToken } = useAuth();
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchClients = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/clients?search=${search}`, { 
        // FIX: Use adminToken
        headers: { Authorization: `Bearer ${adminToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setClients(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminProtectedRoute>
      <div className="space-y-6 p-6">
        <h1 className="text-3xl font-bold text-gray-900">Client Management</h1>
        <Card>
          <CardHeader><CardTitle>Client Lookup</CardTitle></CardHeader>
          <CardContent>
            <div className="flex gap-4 mb-6">
              <Input 
                placeholder="Search clients..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)} 
              />
              <Button onClick={fetchClients} disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </Button>
            </div>
            
            <div className="space-y-4">
              {clients.length === 0 ? (
                 <p className="text-gray-500">No clients found.</p>
              ) : (
                 clients.map(client => (
                    <div key={client.id} className="p-4 border rounded-lg flex justify-between items-center">
                        <div>
                            <p className="font-bold">{client.name}</p>
                            <p className="text-sm text-gray-600">{client.email}</p>
                        </div>
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">ID: {client.id}</span>
                    </div>
                 ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminProtectedRoute>
  );
}