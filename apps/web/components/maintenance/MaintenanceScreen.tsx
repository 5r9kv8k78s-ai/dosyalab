import { Wrench } from 'lucide-react';
import { DosyaLabLogo } from '@/components/brand/DosyaLabLogo';
import { useTranslation } from '@/lib/i18n';

/**
 * Replaces the entire conversion UI (upload zone, tool cards, start action)
 * while Maintenance Mode is on — see MaintenanceGate, which is the only
 * place this is rendered. This is UX only: the backend's own 503 on every
 * conversion-submit route (see app/services/maintenance.py) is what
 * actually stops a request, regardless of whether this screen renders.
 */
export function MaintenanceScreen({ message }: { message: string | null }) {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex min-h-[70vh] w-full max-w-md flex-col items-center justify-center px-5 py-16 text-center sm:px-6">
      <DosyaLabLogo size={40} />
      <div className="bg-primary-light text-primary mt-8 flex h-14 w-14 items-center justify-center rounded-full">
        <Wrench className="h-6 w-6" aria-hidden="true" />
      </div>
      <h1 className="text-foreground sm:text-h3 mt-6 text-[22px] font-semibold leading-tight">
        {t.maintenance.title}
      </h1>
      <p className="text-muted text-small mt-3 leading-relaxed">
        {message ?? t.maintenance.defaultBody}
      </p>
    </section>
  );
}
