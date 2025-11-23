"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ClientLookupPage() {
  const { token } = useAuth();
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchClients = async () => {
    setLoading(true);
    try {
      // This will now work because of the next.config.mjs fix!
      const res = await fetch(`/clients?search=${search}`, { 
        headers: { Authorization: `Bearer ${token}` }
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
    <div className="space-y-6">
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
          {/* Render your table here */}
          <div className="text-sm text-gray-600">
            {clients.length} clients found.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}