// TEST HARNESS ONLY. No extraction/model fallback is provided here.
import { useSyncExternalStore } from 'react'
const contributions = []
export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar.nav'
export const host = {
  state: { profile: { get: () => 'isolated-ui-qa', subscribe: () => () => {} } },
  request: async () => { throw new Error('Model extraction requires the real Hermes Desktop host. This UI harness does not simulate it.') },
}
export const useValue = atom => useSyncExternalStore(atom.subscribe, atom.get, atom.get)
export const gatewayActivationEpoch = () => 1
export const captureGatewayFileDownload = () => async (path, name) => {
  const response = await fetch(`/test/download?path=${encodeURIComponent(path)}`)
  if (!response.ok) throw new Error('Test export download failed')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = name; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
export const ctx = {
  registerMany: items => { contributions.push(...items) },
  rest: async (path, opts = {}) => {
    const response = await fetch(`/api/plugins/formwork${path}`, { method: opts.method || 'GET', body: opts.body ? JSON.stringify(opts.body) : undefined, headers: opts.body ? { 'Content-Type': 'application/json' } : {} })
    const data = await response.json()
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data))
    return data
  },
  files: {
    requestFolder: async () => ({ ok: true, folder: { id: 'test-fixtures', name: 'Original synthetic fixtures', path: 'TEST ONLY' } }),
    list: async () => (await fetch('/test/folder')).json(),
    readDataUrl: async (id, name) => (await fetch(`/test/read?name=${encodeURIComponent(name)}`)).json(),
  },
}
export const pageContribution = () => contributions.find(item => item.area === ROUTES_AREA)
