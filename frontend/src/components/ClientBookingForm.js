
"use client";

import React, { useContext } from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AuthContext } from "@/context/AuthContext";
import AIChat from "@/components/AIChat";

export default function ClientBookingForm({ complaint, setComplaint, aiChatRef }) {
  const { userRole, logout } = useContext(AuthContext);
  const router = useRouter();

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-lg">
      <CardHeader className="border-b bg-zinc-50 dark:bg-zinc-900">
        <CardTitle className="text-2xl text-center">Veterinary Intake Coordinator</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {userRole === 'admin' && (
           <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 m-4" role="alert">
             <p className="font-bold">Staff Account Detected</p>
             <p>You are logged in as a staff member. You cannot book client appointments from this form.</p>
             <Button variant="link" onClick={logout} className="p-0 h-auto font-bold underline">Log out</Button>
           </div>
        )}
        
        <div className="p-6">
          <AIChat ref={aiChatRef} complaint={complaint} />
        </div>
      </CardContent>
    </Card>
  );
}
