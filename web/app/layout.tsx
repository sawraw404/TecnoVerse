import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "TecnoVerse", template: "%s · TecnoVerse" },
  description:
    "Virtual Science Park for Blue Science Park: company profiles with sources, matched funding, events and test environments, and a guarded assistant.",
  robots: { index: false, follow: false }, // prototype with simulated login
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f5" },
    { media: "(prefers-color-scheme: dark)", color: "#0b141c" },
  ],
};

// Runs before the first paint: the saved choice from the sidebar toggle, else the computer's setting.
const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("tv-theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}})()`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // the theme attribute is set by THEME_SCRIPT before React loads, so it differs from the server HTML
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full">
        {children}
        {/* beforeInteractive: injected into the server HTML and run before the page hydrates (no flash) */}
        <Script id="theme" strategy="beforeInteractive" dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </body>
    </html>
  );
}
