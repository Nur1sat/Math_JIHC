import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "math_Mindset",
  description: "math_Mindset оқу платформасы"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="kk">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Lexend:wght@100..900&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-background font-body text-on-background">
        {children}
      </body>
    </html>
  );
}
