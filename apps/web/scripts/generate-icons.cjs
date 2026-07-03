// One-off dev utility: rasterizes the brand SVG marks into the static PNG
// favicon/app-icon sizes Next.js's metadata.icons references. Not part of
// the app bundle — run manually (`node scripts/generate-icons.cjs`)
// whenever public/brand/*.svg changes, then commit the regenerated PNGs.
//
// Uses next/og's ImageResponse (bundled with Next.js — Satori + resvg-wasm
// under the hood) so no extra rasterization dependency is needed. CommonJS
// because next/og only exposes a resolvable entry point via `require()`.
const { ImageResponse } = require('next/og');
const { readFileSync, writeFileSync } = require('node:fs');
const path = require('node:path');

const publicDir = path.join(__dirname, '..', 'public');
const brandDir = path.join(publicDir, 'brand');

function svgDataUri(svgPath) {
  const svg = readFileSync(svgPath, 'utf-8');
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`;
}

async function rasterize(svgPath, size, outFile) {
  const src = svgDataUri(svgPath);
  const response = new ImageResponse(
    { type: 'img', props: { src, width: size, height: size } },
    { width: size, height: size },
  );
  const buffer = Buffer.from(await response.arrayBuffer());
  writeFileSync(outFile, buffer);
  console.log(`wrote ${path.relative(publicDir, outFile)} (${buffer.length} bytes)`);
}

async function main() {
  const faviconMark = path.join(brandDir, 'favicon-mark.svg');
  const logo = path.join(brandDir, 'logo.svg');

  await rasterize(faviconMark, 16, path.join(publicDir, 'favicon-16x16.png'));
  await rasterize(faviconMark, 32, path.join(publicDir, 'favicon-32x32.png'));
  await rasterize(logo, 180, path.join(publicDir, 'apple-touch-icon.png'));
  await rasterize(logo, 512, path.join(publicDir, 'icon-512.png'));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
