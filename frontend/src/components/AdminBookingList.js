"use client";
import React from 'react';
import { Badge } from "@/components/ui/badge"; // Adjust import based on your UI library structure if needed

export default function AdminBookingList({ bookings = [], onDelete }) {
  // Helper function to format time nicely
  const formatTime = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  // Helper for date
  const formatDate = (dateString) => {
    if (!dateString) return "";
    return new Date(dateString).toLocaleDateString();
  };

  if (!bookings || bookings.length === 0) {
    return (
      <div className="text-center p-8 text-gray-500">
        No bookings found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-gray-500 border-b">
            <th className="p-4 font-medium">Time</th>
            <th className="p-4 font-medium">Status</th>
            <th className="p-4 font-medium">Client & Pet</th>
            <th className="p-4 font-medium">Complaint</th>
            <th className="p-4 font-medium">Staff</th>
            <th className="p-4 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((booking) => (
            <tr 
              key={booking.id} 
              // Make row clickable but ignore clicks on action buttons
              onClick={(e) => {
                if (!e.target.closest('button')) {
                  window.location.href = `/admin/bookings/${booking.id}`;
                }
              }}
              className="cursor-pointer hover:bg-gray-50 transition-colors border-b last:border-0"
            >
              {/* Time Column */}
              <td className="p-4">
                <div className="font-bold text-gray-900">
                  {formatTime(booking.start_time)}
                </div>
                <div className="text-xs text-gray-500">
                  {formatDate(booking.start_time)}
                </div>
              </td>

              {/* Status Badge */}
              <td className="p-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                  ${booking.status === 'confirmed' ? 'bg-green-100 text-green-800' : 
                    booking.status === 'cancelled' ? 'bg-red-100 text-red-800' : 
                    'bg-yellow-100 text-yellow-800'}`}>
                  {booking.status}
                </span>
              </td>

              {/* Client & Pet */}
              <td className="p-4">
                <div className="font-medium text-gray-900">
                  {booking.client?.name || "Unknown Owner"}
                </div>
                <div className="text-sm text-gray-500">
                  Pet: {booking.pet?.name || "N/A"}
                </div>
              </td>

              {/* Complaint */}
              <td className="p-4 max-w-xs truncate text-gray-600" title={booking.complaint_reason}>
                {booking.complaint_reason || "No notes provided"}
              </td>

              {/* Staff */}
              <td className="p-4 text-gray-900">
                Dr. {booking.staff?.name || "Unassigned"}
              </td>
              
              {/* Actions */}
              <td className="p-4 text-right">
                {onDelete && (
                  <button 
                    onClick={() => onDelete(booking.id)}
                    className="text-red-600 hover:text-red-800 text-sm font-medium px-3 py-1 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}