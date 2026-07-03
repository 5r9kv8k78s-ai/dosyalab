import { ShieldCheck } from 'lucide-react';
import { ComingSoonCard } from '@/components/conversions/ComingSoonCard';
import { PdfToWordCard } from '@/components/conversions/PdfToWordCard';
import { FileTypeIcon } from '@/components/icons/FileTypeIcon';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col items-center px-6 py-16">
      <section className="max-w-2xl text-center">
        <h1 className="text-h1 sm:text-display">
          Belgelerinizi hızlı, güvenli ve ücretsiz dönüştürün.
        </h1>
        <p className="mt-4 text-body text-muted sm:text-h3 sm:font-normal">
          PDF, Word, Excel ve görsellerinizi saniyeler içinde dönüştürün.
        </p>
      </section>

      <section className="mt-12 grid w-full grid-cols-1 gap-4 sm:grid-cols-2" aria-label="Available conversions">
        <PdfToWordCard />
        <ComingSoonCard
          title="Word → PDF"
          description="Convert .docx files into shareable PDFs"
          icon={<FileTypeIcon type="word" size={40} />}
        />
        <ComingSoonCard
          title="Image → PDF"
          description="Combine images into a single PDF"
          icon={<FileTypeIcon type="image" size={40} />}
        />
        <ComingSoonCard
          title="PDF → Excel"
          description="Extract PDF tables into a spreadsheet"
          icon={<FileTypeIcon type="pdf" size={40} />}
        />
      </section>

      <section className="mt-12 flex w-full max-w-2xl items-center gap-3 rounded-lg border border-primary/20 bg-primary-light px-5 py-4">
        <ShieldCheck className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
        <p className="text-small text-primary">
          Dosyalarınız işlem tamamlandıktan sonra otomatik silinir.
        </p>
      </section>
    </main>
  );
}
