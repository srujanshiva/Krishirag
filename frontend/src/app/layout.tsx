import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KrishiRAG — AI-Based Farmer Query Support & Advisory System",
  description:
    "Authoritative, verified agronomic advisory system for Indian farmers. Grounded exclusively in verified ICAR, TNAU, and KAU crop production guides with strict citation attribution.",
  keywords: [
    "KrishiRAG",
    "Smart India Hackathon",
    "SIH25076",
    "Agriculture",
    "Farmer Advisory",
    "Paddy",
    "Rice",
    "Crop Protection",
    "Kerala Agriculture",
    "ICAR",
    "TNAU",
  ],
  authors: [{ name: "KrishiRAG Team · CSE 473" }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="light">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>{children}</body>
    </html>
  );
}
