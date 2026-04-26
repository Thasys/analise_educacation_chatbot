import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Análise Educacional Comparada',
  description: 'Sistema de análise comparada Brasil × Internacional em educação básica',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body
        style={{
          margin: 0,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif',
          background: '#0b1220',
          color: '#e6edf7',
        }}
      >
        {children}
      </body>
    </html>
  );
}
