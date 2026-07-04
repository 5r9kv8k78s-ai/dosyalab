export function MetricCard({
  label,
  value,
  sublabel,
}: {
  label: string;
  value: string;
  sublabel?: string;
}) {
  return (
    <div className="border-border bg-surface rounded-xl border p-4">
      <p className="text-muted text-small font-medium">{label}</p>
      <p className="text-foreground mt-1.5 text-2xl font-semibold tabular-nums">{value}</p>
      {sublabel && <p className="text-muted mt-0.5 text-xs">{sublabel}</p>}
    </div>
  );
}
