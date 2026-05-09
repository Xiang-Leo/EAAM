import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EAAM | Ancient Chinese Dental Calculus Microbiome",
  description: "A database for querying, filtering, and visualizing the microbial composition of ancient Chinese dental calculus samples.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 min-h-screen flex flex-col text-slate-900`}>
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="flex-shrink-0 flex items-center font-bold text-2xl text-blue-700 tracking-tight">
                  EAAM
                </Link>
                <nav className="ml-10 flex space-x-8">
                  <Link href="/samples" className="text-slate-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                    Samples
                  </Link>
                  <Link href="/taxa/distribution" className="text-slate-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                    Taxon Distribution
                  </Link>
                  <Link href="/taxa/top" className="text-slate-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                    Top Taxa Discovery
                  </Link>
                </nav>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
          {children}
        </main>

        <footer className="bg-white border-t border-slate-200 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-slate-500 text-sm">
            &copy; {new Date().getFullYear()} EAAM Project. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
  );
}
