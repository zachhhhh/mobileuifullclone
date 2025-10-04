import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Clone Intake Portal',
  description: 'Upload IPA/APK binaries for automated analysis runs.'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <main className="min-h-screen flex flex-col items-center py-10 px-4">{children}</main>
      </body>
    </html>
  );
}
