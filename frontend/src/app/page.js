import ClientBookingForm from "@/components/ClientBookingForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="container mx-auto py-12 px-4">
        <h1 className="text-4xl font-bold mb-6 text-zinc-900 dark:text-zinc-50">Client Portal</h1>
        <div className="max-w-xl">
          <ClientBookingForm />
        </div>
      </main>
    </div>
  );
}
