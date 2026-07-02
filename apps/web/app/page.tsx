import { ComingSoonCard } from '@/components/conversions/ComingSoonCard';
import { PdfToWordCard } from '@/components/conversions/PdfToWordCard';
import { HealthStatus } from '@/components/HealthStatus';

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center px-6 py-16">
      <div className="mb-8 flex w-full items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">FormatFlow</h1>
        <HealthStatus />
      </div>

      <p className="mb-10 max-w-xl text-center text-gray-500">
        Pick a conversion below and drop in your file. FormatFlow converts it on the server and
        sends the result straight back to your browser.
      </p>

      <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
        <PdfToWordCard />
        <ComingSoonCard title="Word → PDF" description="Convert .docx files into shareable PDFs" />
        <ComingSoonCard title="Image → PDF" description="Combine images into a single PDF" />
        <ComingSoonCard title="PDF → Excel" description="Extract PDF tables into a spreadsheet" />
      </div>
    </main>
  );
}
