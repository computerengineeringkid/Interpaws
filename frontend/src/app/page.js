"use client";

import { useState, useRef } from "react";
import ClientBookingForm from "@/components/ClientBookingForm";
import AIChat from "@/components/AIChat";

export default function Home() {
  const [complaint, setComplaint] = useState("");
  const aiChatRef = useRef(null);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="container mx-auto py-12 px-4">
        <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50 text-center">Client Portal</h1>
        <div className="max-w-4xl mx-auto space-y-8">
          <ClientBookingForm complaint={complaint} setComplaint={setComplaint} aiChatRef={aiChatRef} />
        </div>
      </main>
    </div>
  );
}
