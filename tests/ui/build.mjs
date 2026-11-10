// Development-only dependencies: npm install --prefix .cache/ui-tools esbuild react react-dom playwright
import path from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const repo = path.resolve(import.meta.dirname, '../..')
const esbuild = require(path.join(repo, '.cache/ui-tools/node_modules/esbuild'))
await esbuild.build({
  entryPoints: [path.join(import.meta.dirname, 'entry.js')], bundle: true, format: 'esm', target: 'es2022',
  outfile: path.join(repo, '.cache/ui-harness/browser.mjs'),
  nodePaths: [path.join(repo, '.cache/ui-tools/node_modules')],
  alias: { '@hermes/plugin-sdk': path.join(import.meta.dirname, 'sdk.js') },
  define: { 'process.env.NODE_ENV': '"development"' },
})
console.log('Built isolated UI QA bundle; production plugin remains uncompiled.')
