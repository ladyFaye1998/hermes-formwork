import React from 'react'
import { createRoot } from 'react-dom/client'
import plugin from '../../desktop/plugin.js'
import { ctx, pageContribution } from './sdk.js'
plugin.register(ctx)
const page = pageContribution()
if (!page) throw new Error('The plugin did not register its native route contribution.')
createRoot(document.getElementById('root')).render(page.render())
