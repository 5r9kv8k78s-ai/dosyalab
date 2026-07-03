import { ShieldCheck } from 'lucide-react';
import { ImageToPdfCard } from '@/components/conversions/ImageToPdfCard';
import { MergePdfCard } from '@/components/conversions/MergePdfCard';
import { PdfToExcelCard } from '@/components/conversions/PdfToExcelCard';
import { PdfToWordCard } from '@/components/conversions/PdfToWordCard';
import { WordToPdfCard } from '@/components/conversions/WordToPdfCard';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col items-center px-6 py-16">
      <section className="max-w-2xl text-center">
        <h1 className="text-h1 sm:text-display">
          Belgelerinizi hızlı, güvenli ve ücretsiz dönüştürün.
        </h1>
        <p className="text-body text-muted sm:text-h3 mt-4 sm:font-normal">
          PDF, Word, Excel ve görsellerinizi saniyeler içinde dönüştürün.
        </p>
      </section>

      <section
        className="mt-12 grid w-full grid-cols-1 gap-4 sm:grid-cols-2"
        aria-label="Available conversions"
      >
        <PdfToWordCard />
        <WordToPdfCard />
        <ImageToPdfCard />
        <PdfToExcelCard />
        <MergePdfCard />
      </section>

      <section className="border-primary/20 bg-primary-light mt-12 flex w-full max-w-2xl items-center gap-3 rounded-lg border px-5 py-4">
        <ShieldCheck className="text-primary h-5 w-5 shrink-0" aria-hidden="true" />
        <p className="text-small text-primary">
          Dosyalarınız işlem tamamlandıktan sonra otomatik silinir.
        </p>
      </section>
    </main>
  );
}
