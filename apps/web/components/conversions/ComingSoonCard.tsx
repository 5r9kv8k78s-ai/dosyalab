interface ComingSoonCardProps {
  title: string;
  description: string;
}

export function ComingSoonCard({ title, description }: ComingSoonCardProps) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 opacity-60">
      <div>
        <h2 className="font-semibold text-gray-500">{title}</h2>
        <p className="mt-1 text-sm text-gray-400">{description}</p>
      </div>
      <span className="mt-4 inline-block w-fit rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-500">
        Coming soon
      </span>
    </div>
  );
}
