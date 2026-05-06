import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { ProfileTheme } from '@/components/layout/ProfileTheme';
import { QueryProvider } from '@/components/layout/QueryProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'EduCompara — Análise Educacional Comparada',
  description: 'Sistema de análise comparada Brasil × Internacional em educação básica',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <QueryProvider>
          <ProfileTheme />
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
