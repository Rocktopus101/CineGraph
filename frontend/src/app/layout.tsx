import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/lib/query-provider";
import { Navbar } from "@/components/layout/Navbar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "CineGraph",
  description: "AI-powered movie recommendations from your Letterboxd history",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans`}>
        <QueryProvider>
          <AuthProvider>
            <Navbar />
            <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
