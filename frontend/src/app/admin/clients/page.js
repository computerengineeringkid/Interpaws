"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ClientLookupPage() {
  const { token } = useAuth();
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  // We need to add a search/list endpoint to the backend or just list all
  // For now, let's assume we fetch all and filter client-side or add a search param if supported
  const fetchClients = async () => {
    setLoading(true);
    try {
      // NOTE: You might need to ensure this endpoint exists in your backend or create it.
      // Usually GET /clients/ (admin only)
      const res = await fetch(`/clients?search=${search}`, { 
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        // If the API returns a list, set it. If it returns { items: [] }, adapt accordingly.
        setClients(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Failed to fetch clients", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchClients();
  }, [token]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Client Management</h1>

      <Card>
        <CardHeader>
          <CardTitle>Client Lookup</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6">
            <Input 
              placeholder="Search by name or email..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
            <Button onClick={fetchClients} disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>

          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="p-4 font-medium text-gray-500">Name</th>
                  <th className="p-4 font-medium text-gray-500">Email</th>
                  <th className="p-4 font-medium text-gray-500">ID</th>
                  <th className="p-4 font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {clients.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="p-4 text-center text-gray-500">No clients found</td>
                  </tr>
                ) : (
                  clients.map((client) => (
                    <tr key={client.id} className="border-b hover:bg-gray-50">
                      <td className="p-4 font-medium">{client.name}</td>
                      <td className="p-4">{client.email}</td>
                      <td className="p-4 text-gray-500">#{client.id}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${client.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'}`}>
                          {client.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}