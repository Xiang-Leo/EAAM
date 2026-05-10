import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'EAAM | Ancient Calculus Microbiome Database',
  description: 'Query, filter, and visualize the microbial composition of ancient Chinese dental calculus samples.',
};

const NAV = [
  { href: '/',                label: 'Dashboard' },
  { href: '/samples',        label: 'Samples' },
  { href: '/taxa',           label: 'Taxa' },
  { href: '/taxa/distribution', label: 'Distribution' },
  { href: '/ai-query',       label: 'AI Query' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        {/* Top navigation */}
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-14 gap-6">
            <Link href="/" className="font-bold text-lg text-indigo-700 tracking-tight shrink-0">
              EAAM
            </Link>
            <div className="flex gap-1 overflow-x-auto">
              {NAV.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="px-3 py-1.5 rounded-md text-sm text-gray-600 hover:text-indigo-700 hover:bg-indigo-50 transition-colors whitespace-nowrap"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        {/* Page content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-gray-200 mt-16 py-6 text-center text-xs text-gray-400">
          © {new Date().getFullYear()} EAAM Project
        </footer>
      </body>
    </html>
  );
}
