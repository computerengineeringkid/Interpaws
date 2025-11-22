"use client";

import { useState, useRef } from "react";
import Navigation from "@/components/Navigation";
import ClientBookingForm from "@/components/ClientBookingForm";

export default function Home() {
  const [complaint, setComplaint] = useState("");
  const aiChatRef = useRef(null);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="container mx-auto py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <ClientBookingForm complaint={complaint} setComplaint={setComplaint} aiChatRef={aiChatRef} />
        </div>
      </main>
    </div>
  );
}
