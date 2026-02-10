'use client';

import { useLocale } from 'next-intl';
import { usePathname, useRouter } from 'next/navigation';
import { locales, localeNames, type Locale } from '@/i18n';
import { Button } from '@/components/ui/button';

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const switchLocale = (newLocale: Locale) => {
    // Replace the current locale in the pathname with the new one
    const segments = pathname.split('/');
    segments[1] = newLocale;
    const newPathname = segments.join('/');
    router.push(newPathname);
  };

  return (
    <div className="flex items-center gap-2">
      {locales.map((loc) => (
        <Button
          key={loc}
          variant={loc === locale ? 'default' : 'ghost'}
          size="sm"
          onClick={() => switchLocale(loc)}
          className={loc === locale ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'text-gray-600 hover:text-indigo-400'}
        >
          {localeNames[loc]}
        </Button>
      ))}
    </div>
  );
}
