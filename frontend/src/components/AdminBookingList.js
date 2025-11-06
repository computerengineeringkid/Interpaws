import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function AdminBookingList() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin: Booking List</CardTitle>
      </CardHeader>
      <CardContent>
        <p>Upcoming bookings will be listed here.</p>
      </CardContent>
    </Card>
  );
}
