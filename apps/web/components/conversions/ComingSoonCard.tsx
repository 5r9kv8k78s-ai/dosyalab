import type { ReactNode } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

interface ComingSoonCardProps {
  title: string;
  description: string;
  icon?: ReactNode;
}

export function ComingSoonCard({ title, description, icon }: ComingSoonCardProps) {
  return (
    <Card className="flex flex-col justify-between border-dashed bg-background">
      <div>
        {/* Opacity here is purely decorative fade on the icon graphic — text
            below uses the `muted` token directly so its contrast ratio isn't
            degraded by a blanket opacity (that previously dropped effective
            contrast under WCAG AA; verified with Lighthouse). */}
        {icon && <div className="mb-3 opacity-60">{icon}</div>}
        <h2 className="font-semibold text-muted">{title}</h2>
        <p className="mt-1 text-small text-muted">{description}</p>
      </div>
      <Badge variant="neutral" className="mt-4 w-fit">
        Coming soon
      </Badge>
    </Card>
  );
}
