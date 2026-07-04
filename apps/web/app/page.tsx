import { ConversionFlow } from '@/components/home/ConversionFlow';
import { Hero } from '@/components/home/Hero';
import { JsonLd } from '@/components/seo/JsonLd';
import { SITE_URL } from '@/lib/seo/siteUrl';

// Minimal, truthful WebApplication structured data — no ratings, reviews,
// prices, or user/download counts, since none of those exist for DosyaLab.
const WEB_APPLICATION_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'DosyaLab',
  url: SITE_URL,
  applicationCategory: 'UtilitiesApplication',
  operatingSystem: 'Any',
  description:
    'PDF, Word, Excel ve görsel dosyalarınızı tarayıcınızdan dönüştürün, birleştirin ve düzenleyin.',
  inLanguage: ['tr', 'en'],
};

export default function Home() {
  return (
    <main>
      <JsonLd data={WEB_APPLICATION_JSON_LD} />
      <Hero />
      <ConversionFlow />
    </main>
  );
}
