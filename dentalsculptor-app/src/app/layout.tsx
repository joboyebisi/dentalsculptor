import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import { ClerkProvider } from "@clerk/nextjs";
import { PostHogProvider } from "@/components/providers/posthog-provider";
import { PreviewBanner } from "@/components/layout/preview-banner";
import { APP_NAME, APP_TAGLINE } from "@/lib/constants";
import { isUiPreviewMode } from "@/lib/preview-mode";
import "./globals.css";

function hasClerkKeys(): boolean {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  return Boolean(key && key.startsWith("pk_"));
}

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: {
    default: `${APP_NAME} | ${APP_TAGLINE}`,
    template: `%s | ${APP_NAME}`,
  },
  description:
    "Upload dental images and generate editable 3D models for teaching, assessment, and immersive learning.",
  icons: {
    icon: [
      { url: "/icon.png", type: "image/png", sizes: "32x32" },
      { url: "/favicon.png", type: "image/png", sizes: "32x32" },
    ],
    apple: [{ url: "/apple-icon.png", type: "image/png", sizes: "180x180" }],
    shortcut: "/favicon.png",
  },
};

function AppBody({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <PreviewBanner />
        <Suspense fallback={null}>
          <PostHogProvider>{children}</PostHogProvider>
        </Suspense>
      </body>
    </html>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const body = <AppBody>{children}</AppBody>;

  // Clerk required for sign-in even when UI_PREVIEW_MODE bypasses auth middleware
  if (hasClerkKeys()) {
    return <ClerkProvider>{body}</ClerkProvider>;
  }

  if (isUiPreviewMode()) {
    return body;
  }

  return <ClerkProvider>{body}</ClerkProvider>;
}
