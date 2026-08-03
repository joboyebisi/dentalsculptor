import type { Metadata } from "next";
// import { Geist, Geist_Mono } from "next/font/google"; // Commented out Geist
import { Inter } from "next/font/google"; // Added Inter
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Toaster } from "@/components/ui/sonner"; // Added import
// import { ModelProvider } from "../context/model-context"; // Using alias path
import { ModelProvider } from "@/context/model-context";
import { AuthProvider } from "@/lib/firebase/AuthContext";

// Commented out Geist setup
// const geistSans = Geist({
//   variable: "--font-geist-sans",
//   subsets: ["latin"],
// });

// const geistMono = Geist_Mono({
//   variable: "--font-geist-mono",
//   subsets: ["latin"],
// });

// Added Inter setup
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Bloom - 3D Dental Models",
  description: "Generate 3D dental models from images.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        // Updated className to use Inter font
        // className={`${geistSans.variable} ${geistMono.variable} antialiased flex flex-col min-h-screen`}
        className={`${inter.className} antialiased flex flex-col min-h-screen`}
      >
        <AuthProvider>
          <ModelProvider>
            <Navbar />
            <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </main>
            <Footer />
            <Toaster />
          </ModelProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
