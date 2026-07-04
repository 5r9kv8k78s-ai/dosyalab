import type { DailyActivityItem } from '@/lib/admin/adminApi';

const CHART_HEIGHT = 160;
const BAR_GAP = 8;

/** Accessible, dependency-free SVG bar chart — stacked successes (teal) +
 * failures/rejections (slate) per day. Paired with a visually hidden
 * `<table>` carrying the same data as text, for screen readers and
 * anything that can't parse the SVG. */
export function ActivityChart({ days }: { days: DailyActivityItem[] }) {
  if (days.length === 0) {
    return (
      <div className="text-muted text-small border-border bg-surface flex h-40 items-center justify-center rounded-xl border">
        Bu aralıkta veri yok.
      </div>
    );
  }

  const maxAttempts = Math.max(...days.map((d) => d.attempts), 1);
  const barWidth = Math.max(100 / days.length - 2, 4);

  return (
    <div className="border-border bg-surface rounded-xl border p-4">
      <svg
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-40 w-full"
        role="img"
        aria-label={`Son ${days.length} güne ait günlük dönüştürme etkinliği`}
      >
        {days.map((day, index) => {
          const x = index * (100 / days.length) + 1;
          const successHeight = (day.successes / maxAttempts) * (CHART_HEIGHT - BAR_GAP);
          const failureHeight =
            (day.failures_or_rejections / maxAttempts) * (CHART_HEIGHT - BAR_GAP);
          const totalHeight = successHeight + failureHeight;
          const y = CHART_HEIGHT - totalHeight;

          return (
            <g key={day.day}>
              <title>
                {day.day}: {day.attempts} işlem, {day.successes} başarılı,{' '}
                {day.failures_or_rejections} başarısız/red
              </title>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={failureHeight}
                fill="rgb(var(--color-muted))"
                opacity={0.5}
              />
              <rect
                x={x}
                y={y + failureHeight}
                width={barWidth}
                height={successHeight}
                fill="rgb(var(--color-primary))"
              />
            </g>
          );
        })}
      </svg>

      <div className="text-muted mt-2 flex items-center gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="bg-primary inline-block h-2 w-2 rounded-full" /> Başarılı
        </span>
        <span className="flex items-center gap-1.5">
          <span className="bg-muted inline-block h-2 w-2 rounded-full opacity-50" /> Başarısız / Red
        </span>
      </div>

      <table className="sr-only">
        <caption>Günlük dönüştürme etkinliği</caption>
        <thead>
          <tr>
            <th scope="col">Tarih</th>
            <th scope="col">Toplam işlem</th>
            <th scope="col">Başarılı</th>
            <th scope="col">Başarısız / Red</th>
          </tr>
        </thead>
        <tbody>
          {days.map((day) => (
            <tr key={day.day}>
              <td>{day.day}</td>
              <td>{day.attempts}</td>
              <td>{day.successes}</td>
              <td>{day.failures_or_rejections}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
