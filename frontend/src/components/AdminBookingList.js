// frontend/src/components/AdminBookingList.js

// 1. Add this helper function at the top of your component
const formatTime = (dateString) => {
  return new Date(dateString).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

// 2. Update your Table Row rendering
// Note: We added an onClick to the row for your "Click into booking" request
{bookings.map((booking) => (
  <tr 
    key={booking.id} 
    onClick={() => window.location.href = `/admin/bookings/${booking.id}`} // Simple navigation
    className="cursor-pointer hover:bg-gray-50 transition-colors"
  >
    {/* Time Column (Fixed 12-hour format) */}
    <td className="p-4">
      <div className="font-bold">{formatTime(booking.start_time)}</div>
      <div className="text-xs text-gray-500">
        {new Date(booking.start_time).toLocaleDateString()}
      </div>
    </td>

    {/* Status Badge (Keep your existing logic here) */}
    <td className="p-4">
      <span className={`badge badge-${booking.status.toLowerCase()}`}>
        {booking.status}
      </span>
    </td>

    {/* Client & Pet (The new info!) */}
    <td className="p-4">
      <div className="font-medium">{booking.client?.name || "Unknown Owner"}</div>
      <div className="text-sm text-gray-500">Pet: {booking.pet?.name || "N/A"}</div>
    </td>

    {/* Complaint / Reason */}
    <td className="p-4 max-w-xs truncate" title={booking.complaint_reason}>
      {booking.complaint_reason || "No notes provided"}
    </td>

    {/* Staff */}
    <td className="p-4">
      Dr. {booking.staff?.name || "Unassigned"}
    </td>
    
    {/* Actions */}
    <td className="p-4">
       {/* Keep your delete/edit buttons here */}
    </td>
  </tr>
))}