'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { getMaintenanceStatus, type MaintenanceStatus } from '@/lib/api';
import { MaintenanceScreen } from './MaintenanceScreen';

const NOT_IN_MAINTENANCE: MaintenanceStatus = { enabled: false, message: null };

/**
 * The only place `MaintenanceScreen` is rendered. Renders the homepage's
 * normal conversion UI immediately — `children` is never held back waiting
 * on a backend response (the API runs on Render's free tier, where a cold
 * start can take 50s+; blocking the homepage on that is unacceptable) —
 * then swaps to the maintenance screen only if a client-side check, fired
 * once on mount, comes back `enabled: true`.
 *
 * Purely a presentation/gating layer: `getMaintenanceStatus` (see lib/
 * api.ts) already has its own timeout and catches every network/parse
 * error, resolving to "not in maintenance" rather than rejecting — so a
 * slow, unreachable, or erroring backend just leaves the normal site
 * showing, never an error screen. The actual enforcement boundary is the
 * backend's own `enforce_not_in_maintenance` guard on every conversion-
 * submit route (see app/services/maintenance.py) — unaffected by whatever
 * this component does or fails to do.
 *
 * Deliberately a single check on mount, not a polling loop — an admin
 * flipping Maintenance Mode on mid-session is not a scenario this needs to
 * react to within seconds.
 */
export function MaintenanceGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<MaintenanceStatus>(NOT_IN_MAINTENANCE);

  useEffect(() => {
    let cancelled = false;
    getMaintenanceStatus()
      .then((next) => {
        if (!cancelled) setStatus(next);
      })
      .catch(() => {
        // Belt-and-suspenders: getMaintenanceStatus already resolves
        // fail-open on its own, but a rejection here must never surface
        // as an unhandled error — it just leaves NOT_IN_MAINTENANCE.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status.enabled) {
    return <MaintenanceScreen message={status.message} />;
  }

  return <>{children}</>;
}
