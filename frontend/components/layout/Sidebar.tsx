'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { GraduationCap, Library, MessageSquare, Settings, Table2 } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV: NavItem[] = [
  { href: '/compare', label: 'Comparar', icon: MessageSquare },
  { href: '/explorer', label: 'Explorador', icon: Table2 },
  { href: '/library', label: 'Biblioteca', icon: Library },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[260px] flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <GraduationCap className="h-6 w-6 text-primary" aria-hidden />
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold">EduCompara</span>
          <span className="text-xs text-muted-foreground">BR × Internacional</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                    active
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-border p-3">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
        >
          <Settings className="h-4 w-4" aria-hidden />
          Configurações
        </button>
      </div>
    </aside>
  );
}
