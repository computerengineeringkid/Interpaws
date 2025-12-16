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
  Mail, Send, Sparkles, Plus, FileText, Users,
  Clock, CheckCircle, AlertCircle, Eye
} from "lucide-react";

const CAMPAIGN_TYPES = [
  { id: "reminder", label: "Appointment Reminder" },
  { id: "vaccination_due", label: "Vaccination Due" },
  { id: "checkup_reminder", label: "Wellness Checkup" },
  { id: "follow_up", label: "Follow-up" },
  { id: "promotion", label: "Promotion" },
];

const TONES = [
  { id: "friendly", label: "Friendly" },
  { id: "professional", label: "Professional" },
  { id: "urgent", label: "Urgent" },
];

export default function OutreachPage() {
  return (
    <AdminProtectedRoute>
      <OutreachContent />
    </AdminProtectedRoute>
  );
}

function OutreachContent() {
  const { adminToken } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [emailHistory, setEmailHistory] = useState([]);
  const [clients, setClients] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("compose");
  const [showPreview, setShowPreview] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [emailForm, setEmailForm] = useState({
    campaign_type: "reminder",
    tone: "friendly",
    context: "",
    client_name: "",
    pet_name: "",
    subject: "",
    body: "",
    to_email: "",
  });

  const fetchData = async () => {
    if (!adminToken) return;
    setIsLoading(true);
    try {
      const [campaignsRes, sendsRes, clientsRes] = await Promise.all([
        fetchWithAuth("/api/email/campaigns", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
        fetchWithAuth("/api/email/sends", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
        fetchWithAuth("/api/clients?per_page=100", {
          headers: { Authorization: `Bearer ${adminToken}` },
        }),
      ]);

      if (campaignsRes.ok) setCampaigns(await campaignsRes.json());
      if (sendsRes.ok) setEmailHistory(await sendsRes.json());
      if (clientsRes.ok) {
        const data = await clientsRes.json();
        setClients(data.clients || []);
      }
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (adminToken) fetchData();
  }, [adminToken]);

  const handleGenerateEmail = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetchWithAuth("/api/email/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify({
          campaign_type: emailForm.campaign_type,
          tone: emailForm.tone,
          context: emailForm.context,
          client_name: emailForm.client_name,
          pet_name: emailForm.pet_name,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setEmailForm({
          ...emailForm,
          subject: data.subject,
          body: data.body,
        });
        setShowPreview(true);
      } else {
        throw new Error("Failed to generate email");
      }
    } catch (err) {
      setError("Failed to generate email. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendEmail = async () => {
    if (!emailForm.to_email || !emailForm.subject || !emailForm.body) {
      setError("Please fill in all required fields");
      return;
    }

    setIsSending(true);
    setError(null);
    try {
      const response = await fetchWithAuth("/api/email/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify({
          to_email: emailForm.to_email,
          subject: emailForm.subject,
          body: emailForm.body,
        }),
      });

      if (response.ok) {
        setSuccess(`Email sent successfully to ${emailForm.to_email}`);
        setEmailForm({
          campaign_type: "reminder",
          tone: "friendly",
          context: "",
          client_name: "",
          pet_name: "",
          subject: "",
          body: "",
          to_email: "",
        });
        setShowPreview(false);
        fetchData();
      } else {
        const data = await response.json();
        throw new Error(data.detail || "Failed to send email");
      }
    } catch (err) {
      setError(err.message || "Failed to send email");
    } finally {
      setIsSending(false);
    }
  };

  const handleSelectClient = (client) => {
    setEmailForm({
      ...emailForm,
      client_name: client.name,
      to_email: client.email,
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      sent: "bg-green-100 text-green-800",
      pending: "bg-yellow-100 text-yellow-800",
      failed: "bg-red-100 text-red-800",
      delivered: "bg-blue-100 text-blue-800",
      opened: "bg-indigo-100 text-indigo-800",
    };
    return styles[status] || "bg-zinc-100 text-zinc-800";
  };

  return (
    <main className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
          Client Outreach
        </h1>
        <p className="text-zinc-500 mt-1">Send emails to clients with AI-powered content generation</p>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto">&times;</button>
        </div>
      )}

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" />
          {success}
          <button onClick={() => setSuccess(null)} className="ml-auto">&times;</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 border-b pb-4">
        {[
          { id: "compose", label: "Compose Email", icon: Mail },
          { id: "history", label: "Send History", icon: Clock },
          { id: "campaigns", label: "Campaigns", icon: FileText },
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

      {/* Compose Tab */}
      {activeTab === "compose" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Email Composer */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-indigo-600" />
                  AI Email Generator
                </CardTitle>
                <CardDescription>
                  Let AI help you write the perfect email
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Email Type</Label>
                    <select
                      value={emailForm.campaign_type}
                      onChange={(e) => setEmailForm({ ...emailForm, campaign_type: e.target.value })}
                      className="w-full h-10 rounded-md border border-input bg-background px-3"
                    >
                      {CAMPAIGN_TYPES.map((type) => (
                        <option key={type.id} value={type.id}>{type.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label>Tone</Label>
                    <select
                      value={emailForm.tone}
                      onChange={(e) => setEmailForm({ ...emailForm, tone: e.target.value })}
                      className="w-full h-10 rounded-md border border-input bg-background px-3"
                    >
                      {TONES.map((tone) => (
                        <option key={tone.id} value={tone.id}>{tone.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Client Name (optional)</Label>
                    <Input
                      value={emailForm.client_name}
                      onChange={(e) => setEmailForm({ ...emailForm, client_name: e.target.value })}
                      placeholder="e.g., John Smith"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Pet Name (optional)</Label>
                    <Input
                      value={emailForm.pet_name}
                      onChange={(e) => setEmailForm({ ...emailForm, pet_name: e.target.value })}
                      placeholder="e.g., Max"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Additional Context (optional)</Label>
                  <Textarea
                    value={emailForm.context}
                    onChange={(e) => setEmailForm({ ...emailForm, context: e.target.value })}
                    placeholder="Any specific details to include in the email..."
                    rows={2}
                  />
                </div>

                <Button
                  onClick={handleGenerateEmail}
                  disabled={isGenerating}
                  className="w-full gap-2"
                >
                  <Sparkles className="h-4 w-4" />
                  {isGenerating ? "Generating..." : "Generate Email with AI"}
                </Button>
              </CardContent>
            </Card>

            {/* Email Preview/Editor */}
            {(showPreview || emailForm.subject || emailForm.body) && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Eye className="h-5 w-5" />
                    Email Preview
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>To Email *</Label>
                    <Input
                      type="email"
                      value={emailForm.to_email}
                      onChange={(e) => setEmailForm({ ...emailForm, to_email: e.target.value })}
                      placeholder="recipient@example.com"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Subject *</Label>
                    <Input
                      value={emailForm.subject}
                      onChange={(e) => setEmailForm({ ...emailForm, subject: e.target.value })}
                      placeholder="Email subject line"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Body *</Label>
                    <Textarea
                      value={emailForm.body}
                      onChange={(e) => setEmailForm({ ...emailForm, body: e.target.value })}
                      rows={10}
                      required
                    />
                  </div>

                  <Button
                    onClick={handleSendEmail}
                    disabled={isSending || !emailForm.to_email}
                    className="w-full gap-2 bg-green-600 hover:bg-green-700"
                  >
                    <Send className="h-4 w-4" />
                    {isSending ? "Sending..." : "Send Email"}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Client List Sidebar */}
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Quick Select Client
              </CardTitle>
              <CardDescription>Click to populate recipient</CardDescription>
            </CardHeader>
            <CardContent>
              {clients.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {clients.slice(0, 20).map((client) => (
                    <button
                      key={client.id}
                      onClick={() => handleSelectClient(client)}
                      className={`w-full text-left p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition ${
                        emailForm.to_email === client.email ? "bg-indigo-50 border border-indigo-200" : ""
                      }`}
                    >
                      <p className="font-medium text-sm">{client.name}</p>
                      <p className="text-xs text-zinc-500">{client.email}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500 text-sm">No clients found</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* History Tab */}
      {activeTab === "history" && (
        <Card>
          <CardHeader>
            <CardTitle>Email Send History</CardTitle>
            <CardDescription>Recent emails sent from this system</CardDescription>
          </CardHeader>
          <CardContent>
            {emailHistory.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Recipient</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Sent At</TableHead>
                    <TableHead>Opened</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {emailHistory.map((email) => (
                    <TableRow key={email.id}>
                      <TableCell>{email.email_address}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(email.status)}`}>
                          {email.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        {email.sent_at
                          ? new Date(email.sent_at).toLocaleString()
                          : "-"}
                      </TableCell>
                      <TableCell>
                        {email.opened_at
                          ? new Date(email.opened_at).toLocaleString()
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-center py-8 text-zinc-500">No emails sent yet</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Campaigns Tab */}
      {activeTab === "campaigns" && (
        <Card>
          <CardHeader>
            <CardTitle>Email Campaigns</CardTitle>
            <CardDescription>Saved campaign templates</CardDescription>
          </CardHeader>
          <CardContent>
            {campaigns.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {campaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell className="font-medium">{campaign.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {campaign.campaign_type}
                        </Badge>
                      </TableCell>
                      <TableCell>{campaign.subject}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(campaign.status)}`}>
                          {campaign.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        {campaign.created_at
                          ? new Date(campaign.created_at).toLocaleDateString()
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-center py-8 text-zinc-500">No campaigns created yet</p>
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
