#!/usr/bin/env node
// Allowlist color→token codemod. Rewrites ONLY exact-matched literals.
// Usage: node scripts/ui/color-codemod.mjs [--dry] <file.css> [more.css ...]
import { readFileSync, writeFileSync } from 'node:fs';

// --- Tokens actually defined in index.css --------------------------------
// Used to gate the dead-fallback pre-pass: only strip `var(--tok, #hex)` ->
// `var(--tok)` when --tok is defined; otherwise the hex fallback is load-
// bearing (the token is undefined) and must be preserved.
const defined = new Set(
  [...readFileSync(new URL('../../frontend/src/index.css', import.meta.url), 'utf8')
     .matchAll(/(--[a-z0-9-]+)\s*:/gi)].map((m) => m[1].toLowerCase())
);

// --- Mapping table: normalized-literal -> replacement -------------------
// Hex keys are lowercase. rgba keys have NO spaces.
const MAP = {
  // neutrals (slate + cool-gray consolidation)
  '#f8fafc': 'var(--gray-50)',
  '#f1f5f9': 'var(--gray-100)', '#f3f4f6': 'var(--gray-100)',
  '#e2e8f0': 'var(--gray-200)', '#e5e7eb': 'var(--gray-200)',
  '#cbd5e1': 'var(--gray-300)', '#d1d5db': 'var(--gray-300)',
  '#94a3b8': 'var(--gray-400)', '#9ca3af': 'var(--gray-400)',
  '#64748b': 'var(--gray-500)', '#6b7280': 'var(--gray-500)',
  '#475569': 'var(--gray-600)', '#4b5563': 'var(--gray-600)',
  '#334155': 'var(--gray-700)', '#374151': 'var(--gray-700)',
  '#1e293b': 'var(--gray-800)', '#1f2937': 'var(--gray-800)',
  '#0f172a': 'var(--gray-900)', '#111827': 'var(--gray-900)',
  '#020617': 'var(--gray-950)',
  // amber scale
  '#fffbeb': 'var(--primary-50)', '#fef3c7': 'var(--primary-100)',
  '#fde68a': 'var(--primary-200)', '#fcd34d': 'var(--primary-300)',
  '#fbbf24': 'var(--primary-400)', '#f59e0b': 'var(--primary-500)',
  '#d97706': 'var(--primary-600)', '#b45309': 'var(--primary-700)',
  // legacy indigo brand -> amber
  '#6366f1': 'var(--primary-500)', '#4f46e5': 'var(--primary-600)',
  '#818cf8': 'var(--primary-400)', '#a5b4fc': 'var(--primary-300)',
  '#4338ca': 'var(--primary-700)',
  // status (danger variants collapse to --danger; slight accepted shift)
  '#22c55e': 'var(--success)',
  '#ef4444': 'var(--danger)', '#dc2626': 'var(--danger)', '#f87171': 'var(--danger)',
  // amber alpha tints
  'rgba(245,158,11,0.05)': 'var(--primary-alpha-05)',
  'rgba(245,158,11,0.1)': 'var(--primary-alpha-10)',
  'rgba(245,158,11,0.15)': 'var(--primary-alpha-15)',
  'rgba(245,158,11,0.2)': 'var(--primary-alpha-20)',
  'rgba(245,158,11,0.3)': 'var(--primary-alpha-30)',
  'rgba(245,158,11,0.4)': 'var(--primary-alpha-40)',
  // status alpha (exact)
  'rgba(34,197,94,0.1)': 'var(--success-bg)',
  'rgba(239,68,68,0.1)': 'var(--danger-bg)',
};

const args = process.argv.slice(2);
const dry = args.includes('--dry');
const files = args.filter((a) => a !== '--dry');

// literal matchers
const HEX = /#[0-9a-fA-F]{3,8}\b/g;
const RGBA = /rgba?\([^)]*\)/g;
const norm = (s) => s.toLowerCase().replace(/\s+/g, '');

for (const file of files) {
  let css = readFileSync(file, 'utf8');
  // pre-pass: drop dead fallbacks  var(--token, #hex) -> var(--token)
  // only when --token is actually defined; otherwise the fallback is real.
  css = css.replace(/var\((--[a-z0-9-]+),\s*#[0-9a-fA-F]{3,8}\)/gi,
    (m, tok) => defined.has(tok.toLowerCase()) ? `var(${tok})` : m);
  const replaced = {}; const unmapped = {};
  const apply = (re) => {
    css = css.replace(re, (m) => {
      const key = norm(m);
      if (MAP[key]) { replaced[m] = (replaced[m] || 0) + 1; return MAP[key]; }
      unmapped[m] = (unmapped[m] || 0) + 1; return m;
    });
  };
  apply(HEX); apply(RGBA);
  if (!dry) writeFileSync(file, css);
  const r = Object.entries(replaced).reduce((a, [, n]) => a + n, 0);
  console.log(`\n${file}  (${r} replaced${dry ? ', DRY' : ''})`);
  const um = Object.entries(unmapped).sort((a, b) => b[1] - a[1]);
  if (um.length) console.log('  UNMAPPED:', um.map(([k, n]) => `${k}×${n}`).join('  '));
}
