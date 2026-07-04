/**
 * Renders a JSON-LD `<script>` tag from a plain object. `JSON.stringify`
 * output is safe inside an HTML `<script type="application/ld+json">`
 * except for the literal substring `</script>`, which would otherwise
 * terminate the tag early and let attacker-controlled data (there is none
 * here today, but this stays correct if a future caller passes dynamic
 * data) break out into raw HTML — escaping the forward slash neutralizes
 * that without changing the parsed JSON value.
 */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  const json = JSON.stringify(data).replace(/</g, '\\u003c');

  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
