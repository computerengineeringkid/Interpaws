import AdminCalendar from "@/components/AdminCalendar";
import AdminBookingList from "@/components/AdminBookingList";
import ClientBookingForm from "@/components/ClientBookingForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="container mx-auto py-12 px-4">
        <div className="flex flex-col gap-8">
          <section>
            <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">
              Admin Dashboard
            </h1>
            <div className="grid gap-6 md:grid-cols-2">
              <AdminCalendar />
              <AdminBookingList />
            </div>
          </section>

          <section>
            <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">
              Client Portal
            </h1>
            <div className="max-w-xl">
              <ClientBookingForm />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
