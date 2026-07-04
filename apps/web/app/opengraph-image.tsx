import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = "DosyaLab — Türkiye'nin dosya platformu";
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

// Same three-segment stroke path as components/brand/DosyaLabLogo.tsx —
// duplicated rather than imported because this route runs on the Edge
// runtime, isolated from the rest of the client component tree.
export default function Image() {
  return new ImageResponse(
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F8FAFC',
        fontFamily: 'sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <svg width={72} height={72} viewBox="0 0 40 40" fill="none">
          <path
            d="M8 27H16L24 13H32"
            stroke="#0D5C54"
            strokeWidth="5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div style={{ display: 'flex', fontSize: 72, fontWeight: 700, color: '#0F172A' }}>
          DosyaLab
        </div>
      </div>
      <div
        style={{ display: 'flex', fontSize: 30, fontWeight: 600, color: '#0D5C54', marginTop: 16 }}
      >
        Türkiye&apos;nin dosya platformu
      </div>
      <div
        style={{
          display: 'flex',
          fontSize: 26,
          fontWeight: 500,
          color: '#64748B',
          marginTop: 32,
          maxWidth: 860,
          textAlign: 'center',
        }}
      >
        Dosyanızı bırakın. Gerisini DosyaLab halletsin.
      </div>
    </div>,
    { ...size },
  );
}
