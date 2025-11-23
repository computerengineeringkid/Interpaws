"use client";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "@/components/Providers";
import Navigation from "@/components/Navigation";
import { usePathname } from "next/navigation";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({ children }) {
  const pathname = usePathname();
  // Hide the main client navigation if we are in the /admin section
  const isAdmin = pathname?.startsWith("/admin");

  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          {/* Only show Client Navigation if NOT in admin */}
          {!isAdmin && <Navigation />}
          
          <main className={!isAdmin ? "min-h-screen bg-gray-50" : ""}>
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}