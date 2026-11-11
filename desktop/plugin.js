import * as SDK from '@hermes/plugin-sdk'
import { createElement as h, useState, useEffect, useMemo, useRef } from 'react'

const { host } = SDK
const ID = 'formwork'
const PATH = '/formwork'
const nonempty = value => value !== null && value !== undefined && value !== '' && value !== false
const text = value => value === null || value === undefined ? '' : String(value)
const valueLabel = (field, value = field.value) => field.type === 'checkbox'
  ? value === true ? 'Checked' : value === false ? 'Unchecked' : 'No answer yet'
  : value !== null && value !== undefined && value !== '' ? text(value) : 'No answer yet'
const label = field => field.label || field.name || 'Untitled field'
const sourceKey = name => text(name).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
const getEpoch = () => typeof SDK.gatewayActivationEpoch === 'function' ? SDK.gatewayActivationEpoch() : host.state.profile.get()
const errorText = error => error?.message || error?.detail || (typeof error === 'string' ? error : 'Something went wrong. Please try again.')

function Icon({ name = 'file', size = 20, ...props }) {
  const paths = {
    file: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z', 'M14 2v6h6', 'M8 13h8', 'M8 17h6'],
    folder: ['M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'],
    plus: ['M12 5v14', 'M5 12h14'],
    arrow: ['M5 12h14', 'm13 6 6 6-6 6'],
    check: ['m5 12 4 4L19 6'],
    close: ['m6 6 12 12', 'M18 6 6 18'],
    left: ['m15 6-6 6 6 6'],
    right: ['m9 6 6 6-6 6'],
    down: ['M12 3v12', 'm7 10 5 5 5-5', 'M5 16v5h14v-5'],
    spark: ['m12 3 2.7 6.3L21 12l-6.3 2.7L12 21l-2.7-6.3L3 12l6.3-2.7z'],
    link: ['M10 13a5 5 0 0 0 7 .2l3-3a5 5 0 0 0-7-7l-2 2', 'M14 11a5 5 0 0 0-7-.2l-3 3a5 5 0 0 0 7 7l2-2'],
    refresh: ['M20 7v5h-5', 'M4 17v-5h5', 'M6.1 7a7 7 0 0 1 11.6-2L20 8', 'M4 16l2.3 3A7 7 0 0 0 18 17'],
    alert: ['M12 3 2 21h20z', 'M12 9v5', 'M12 17h.01'],
    search: ['M21 21l-4.4-4.4', 'M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0'],
    shield: ['m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z', 'm8 12 3 3 5-6'],
    copy: ['M9 9h12v12H9z', 'M15 5V3H3v12h2'],
  }
  return h('svg', { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true, ...props }, ...(paths[name] || paths.file).map((d, i) => h('path', { d, key: i })))
}

function Button({ children, icon, primary, quiet, className = '', ...props }) {
  return h('button', { type: 'button', className: `fw-button ${primary ? 'fw-primary' : ''} ${quiet ? 'fw-quiet' : ''} ${className}`, ...props }, icon && h(Icon, { name: icon, size: 16 }), children)
}
function Pill({ children, tone = '' }) { return h('span', { className: `fw-pill ${tone && `fw-pill-${tone}`}` }, children) }
function Spinner({ children }) { return h('span', { className: 'fw-working', role: 'status' }, h('span', { className: 'fw-spinner' }), children) }

const CSS = `
.fw-modal-evidence-body{flex:1;min-height:0;overflow:auto}.fw-modal-head,.fw-modal-foot{flex-shrink:0}.fw-modal-body{min-height:0}
.fw-batch-item{display:block;border:1px solid var(--fw-line);border-radius:10px;margin-bottom:12px;padding:14px}.fw-batch-item-head{display:flex;gap:10px;align-items:flex-start}.fw-batch-item-head>div{flex:1;min-width:0}.fw-batch-item strong{display:block;font-size:12px;font-weight:600;overflow-wrap:anywhere}.fw-batch-item small{display:block;font-size:10px;color:var(--fw-muted);margin-top:3px}.fw-batch-value{margin:9px 0;color:var(--fw-ink);font-size:15px;white-space:pre-wrap;overflow-wrap:anywhere}.fw-batch-item .fw-quote{margin:9px 0 0;font-size:12px}.fw-zoom{font:inherit;font-size:10px!important;border:1px solid var(--fw-line);border-radius:6px;padding:4px;background:var(--fw-surface);color:var(--fw-muted);max-width:75px}.fw-batch-modal{width:min(680px,100%)}
.fw{--fw-paper:#faf9f6;--fw-surface:#fff;--fw-ink:#282532;--fw-muted:#78747e;--fw-line:#e8e5e9;--fw-plum:#654666;--fw-plum-soft:#f0eaf1;--fw-green:#317360;--fw-green-soft:#eaf5ef;--fw-amber:#94691d;--fw-amber-soft:#fbf1dd;color:var(--fw-ink);background:var(--fw-paper);font-family:var(--ui-font-sans, -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif);height:100%;min-height:0;display:flex;flex-direction:column;font-size:13px;line-height:1.5;isolation:isolate}
.fw *{box-sizing:border-box}.fw button,.fw input,.fw select,.fw textarea{font:inherit}.fw button{cursor:pointer}.fw button:disabled{cursor:default;opacity:.48}.fw button:focus-visible,.fw input:focus-visible,.fw textarea:focus-visible,.fw select:focus-visible{outline:3px solid #bca5c9;outline-offset:3px}.fw svg{flex-shrink:0}.fw h1,.fw h2,.fw h3,.fw p{margin:0}.fw button{transition:background .15s,border-color .15s,box-shadow .15s}.fw-button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:36px;border:1px solid var(--fw-line);border-radius:9px;background:var(--fw-surface);color:var(--fw-ink);padding:7px 12px;font-weight:550;white-space:nowrap}.fw-button:hover:not(:disabled){background:#f1eef2;border-color:#cec4d2}.fw-primary{background:var(--fw-plum);border-color:var(--fw-plum);color:white;box-shadow:0 2px 3px #40274712}.fw-primary:hover:not(:disabled){background:#533654;border-color:#533654}.fw-quiet{border-color:transparent;background:transparent;box-shadow:none;color:var(--fw-muted)}.fw-quiet:hover:not(:disabled){background:#eae5ec}.fw-icon-button{width:30px;min-height:30px;padding:5px}.fw-top{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:84px;padding:19px 30px;background:var(--fw-surface);border-bottom:1px solid var(--fw-line);flex-wrap:wrap}.fw-brand{display:flex;align-items:center;gap:12px}.fw-logo{width:38px;height:38px;border-radius:12px;background:var(--fw-plum);color:white;display:grid;place-items:center;box-shadow:0 3px 10px #65466620}.fw-wordmark{font-size:20px;letter-spacing:-.6px;font-weight:650}.fw-kicker{font-size:10px;letter-spacing:1.8px;font-weight:650;text-transform:uppercase;color:var(--fw-muted)}.fw-tagline{font-size:11px;color:var(--fw-muted)}.fw-steps{display:flex;align-items:center;gap:12px;color:var(--fw-muted);font-size:12px}.fw-step{display:flex;gap:7px;align-items:center}.fw-step-num{display:grid;place-items:center;width:23px;height:23px;border:1px solid var(--fw-line);border-radius:50%;font-size:11px;background:white}.fw-step-active{color:var(--fw-plum);font-weight:600}.fw-step-active .fw-step-num{background:var(--fw-plum);border-color:var(--fw-plum);color:white}.fw-step-done{color:var(--fw-green)}.fw-step-done .fw-step-num{background:var(--fw-green-soft);border-color:#cfe3d8}.fw-step-line{width:28px;height:1px;background:var(--fw-line)}.fw-top-actions{display:flex;align-items:center;gap:8px}.fw-error{display:flex;align-items:flex-start;gap:10px;background:#fff1ed;border-bottom:1px solid #f0cdc3;color:#8d402b;padding:12px 24px;word-break:break-word}.fw-error span{flex:1}.fw-note{display:flex;gap:8px;padding:10px 12px;background:var(--fw-plum-soft);border-radius:9px;color:#674e6a;font-size:12px}.fw-muted{color:var(--fw-muted)}.fw-tiny{font-size:11px}.fw-pill{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:6px;color:var(--fw-muted);background:#f1eff2;font-size:10px;font-weight:600;white-space:nowrap}.fw-pill-green{color:var(--fw-green);background:var(--fw-green-soft)}.fw-pill-amber{color:var(--fw-amber);background:var(--fw-amber-soft)}.fw-pill-plum{color:var(--fw-plum);background:var(--fw-plum-soft)}.fw-working{display:inline-flex;align-items:center;gap:9px;color:var(--fw-plum)}.fw-spinner{width:15px;height:15px;border:2px solid #d8cbdc;border-top-color:var(--fw-plum);border-radius:50%;animation:fw-spin .8s linear infinite}.fw-empty{flex:1;min-height:0;overflow:auto;padding:54px 30px 25px}.fw-empty-inner{max-width:900px;margin:auto;display:grid;grid-template-columns:1.05fr 1fr;align-items:center;gap:60px;min-height:380px}.fw-empty h1{font-family:Georgia,'Times New Roman',serif;font-size:clamp(36px,4vw,54px);font-weight:400;line-height:1.12;letter-spacing:-1.7px;margin:13px 0 19px;max-width:450px}.fw-empty-lead{font-size:15px;line-height:1.8;color:var(--fw-muted);max-width:360px;margin-bottom:24px!important}.fw-empty small{display:block;color:var(--fw-muted);font-size:11px;margin-top:12px}.fw-illustration{position:relative;height:330px;border-radius:32px;background:radial-gradient(ellipse at center,#e8e0ec 0%,#f1edf3 55%,transparent 72%)}.fw-paper-card{position:absolute;left:17%;top:9%;width:64%;height:79%;background:white;border:1px solid #e0d9e3;border-radius:8px;box-shadow:0 13px 50px #49304b12;transform:rotate(-7deg);padding:24px}.fw-paper-card-back{transform:rotate(7deg);left:23%;top:12%;background:#f5f1f6}.fw-paper-head{height:9px;width:47%;background:#806482;border-radius:3px;margin-bottom:18px}.fw-paper-line{height:5px;background:#ede9ef;border-radius:2px;margin-bottom:9px;width:88%}.fw-paper-field{height:27px;border:1px solid #ddd3e1;background:#faf8fb;border-radius:4px;margin-top:15px;display:flex;align-items:center;padding:0 9px}.fw-paper-field::after{content:'';height:4px;width:62%;background:#b39bbb;border-radius:2px}.fw-check-stamp{position:absolute;right:8%;bottom:11%;width:69px;height:69px;border:7px solid var(--fw-paper);border-radius:50%;display:grid;place-items:center;background:var(--fw-green);color:white;box-shadow:0 5px 20px #3173601a}.fw-features{max-width:900px;margin:38px auto 0;display:grid;grid-template-columns:repeat(3,1fr);gap:22px;border-top:1px solid var(--fw-line);padding-top:24px}.fw-feature{display:flex;gap:12px}.fw-feature>svg{color:var(--fw-plum);margin-top:2px}.fw-feature strong{display:block;font-size:12px;font-weight:600;margin-bottom:4px}.fw-feature p{font-size:11px;line-height:1.7;color:var(--fw-muted)}
.fw-body{display:grid;grid-template-columns:215px minmax(280px,1fr) 292px;min-height:0;flex:1}.fw-rail{border-right:1px solid var(--fw-line);padding:22px 14px;overflow:auto;background:#f5f3f5}.fw-rail-heading{display:flex;align-items:center;justify-content:space-between;padding:0 8px 12px}.fw-doc{display:flex;align-items:flex-start;gap:10px;width:100%;text-align:left;border:1px solid transparent;background:transparent;border-radius:10px;padding:12px 9px;color:var(--fw-ink);margin-bottom:4px}.fw-doc:hover{background:#ece7ee}.fw-doc-active{background:white!important;border-color:#dcd1e0;box-shadow:0 2px 5px #33203e05}.fw-doc-icon{width:29px;height:35px;background:#f4edf5;color:#937298;border:1px solid #e9ddec;border-radius:5px;display:grid;place-items:center;flex-shrink:0}.fw-doc-copy{min-width:0;flex:1}.fw-doc-name{font-size:12px;font-weight:550;overflow-wrap:anywhere;display:block}.fw-doc-meta{font-size:10px;color:var(--fw-muted);margin-top:5px;display:flex;align-items:center;gap:6px}.fw-dot{width:5px;height:5px;background:#baa7c3;border-radius:50%;display:inline-block}.fw-dot-green{background:#6a9b7f}.fw-dot-amber{background:#cfaa63}.fw-rail-sources{margin-top:26px;border-top:1px solid var(--fw-line);padding-top:23px}.fw-rail-source{border:0;background:transparent;text-align:left;padding:8px;display:flex;align-items:center;gap:9px;color:var(--fw-muted);font-size:11px;width:100%;border-radius:7px}.fw-rail-source:hover{background:#eae5ec;color:var(--fw-plum)}.fw-rail-source span{overflow-wrap:anywhere}.fw-rail-note{margin:23px 7px 0;font-size:10px;line-height:1.8;color:var(--fw-muted)}.fw-main{display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}.fw-doc-top{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 24px;background:#fffefa;border-bottom:1px solid var(--fw-line)}.fw-doc-top h2{font-size:15px;font-weight:550;letter-spacing:-.2px;overflow-wrap:anywhere}.fw-doc-top .fw-kicker{font-size:9px;letter-spacing:1.4px;margin-bottom:3px}.fw-progress-ring{flex-shrink:0;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--fw-green) calc(var(--fw-progress)*1%),#e5e1e6 0)}.fw-progress-ring span{display:grid;place-items:center;width:31px;height:31px;background:#fffefa;border-radius:50%;font-size:10px;font-weight:600;color:var(--fw-green)}.fw-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 19px;background:#fffefa;border-bottom:1px solid var(--fw-line);font-size:11px;flex-wrap:wrap}.fw-page-control{display:flex;align-items:center;gap:5px;color:var(--fw-muted)}.fw-segmented{display:flex;padding:3px;background:#eeebef;border-radius:7px;gap:2px}.fw-segmented button{border:0;background:transparent;padding:5px 9px;border-radius:5px;font-size:10px;color:var(--fw-muted)}.fw-segmented button[aria-pressed=true]{background:white;color:var(--fw-plum);box-shadow:0 1px 4px #3220380a}.fw-canvas{flex:1;overflow:auto;padding:28px;background:radial-gradient(#ded8e3 .65px,transparent .65px) 0 0/9px 9px;min-height:160px}.fw-sheet{position:relative;width:100%;max-width:780px;margin:0 auto;background:white;box-shadow:0 4px 24px #30243815;min-height:200px;isolation:isolate}.fw-sheet img{display:block;width:100%;height:auto}.fw-field-overlay{position:absolute;min-width:6px;min-height:6px;border:1px solid #a28aaf7a;border-radius:2px;background:#bda2cb12;padding:0;z-index:1;color:var(--fw-plum)}.fw-field-overlay:hover{background:#bda2cb2e;border-color:#795887;z-index:2}.fw-field-overlay-active{outline:2px solid #8c609d;outline-offset:2px;background:#bda2cb25;border-color:#8c609d;z-index:3}.fw-field-overlay-missing{border-color:#cfaa6399;background:#f5c86b12}.fw-field-overlay-reviewed{border-color:#80a38d6b;background:#74b08e08}.fw-field-overlay-label{position:absolute;left:-1px;bottom:calc(100% + 5px);padding:3px 6px;background:var(--fw-plum);color:white;border-radius:4px;white-space:nowrap;max-width:230px;overflow:hidden;text-overflow:ellipsis;font-size:10px;box-shadow:0 2px 5px #0001;pointer-events:none}.fw-render-state{min-height:350px;display:flex;align-items:center;justify-content:center;text-align:center;flex-direction:column;gap:15px;padding:30px;color:var(--fw-muted)}.fw-bottom{padding:10px 20px;background:#fffefa;border-top:1px solid var(--fw-line);font-size:10px;color:var(--fw-muted);display:flex;align-items:center;justify-content:space-between;gap:10px}.fw-bottom kbd{font:inherit;padding:1px 4px;border:1px solid var(--fw-line);border-radius:3px;background:white}.fw-inspector{border-left:1px solid var(--fw-line);background:var(--fw-surface);display:flex;flex-direction:column;min-height:0;overflow:auto}.fw-inspector-head{padding:21px 20px 16px;border-bottom:1px solid var(--fw-line);display:flex;align-items:center;justify-content:space-between}.fw-inspector-body{padding:21px 20px;flex:1}.fw-field-title{font-size:18px;line-height:1.4;font-weight:550;letter-spacing:-.4px;margin:11px 0 18px!important;overflow-wrap:anywhere}.fw-label{display:block;color:var(--fw-muted);font-size:11px;margin-bottom:7px}.fw-input{width:100%;border:1px solid #d9d2dd;border-radius:8px;min-height:39px;padding:9px 10px;background:#fff;color:var(--fw-ink);box-shadow:0 1px 2px #1c102203}.fw-input:focus{border-color:#9b79ad;outline:3px solid #a57eb01c;outline-offset:0}.fw-input-area{resize:vertical;min-height:76px}.fw-checkbox-value{display:flex;align-items:center;gap:10px;border:1px solid var(--fw-line);border-radius:9px;padding:12px}.fw input[type=checkbox]{accent-color:var(--fw-plum);width:15px;height:15px;flex-shrink:0}.fw-save{width:100%;margin-top:12px}.fw-evidence{border-top:1px solid var(--fw-line);margin-top:26px;padding-top:20px}.fw-evidence-title{display:flex;align-items:center;gap:7px;color:var(--fw-muted);font-size:11px;font-weight:550;margin-bottom:11px}.fw-quote{margin:0;padding:12px 13px;border-left:2px solid #b59cc0;background:#f8f5f9;border-radius:0 7px 7px 0;color:#64556c;font-family:Georgia,'Times New Roman',serif;font-size:13px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere}.fw-source-button{border:0;background:transparent;padding:10px 0 0;display:flex;gap:6px;align-items:flex-start;color:var(--fw-plum);font-size:10px;text-align:left}.fw-no-evidence{padding:14px;background:#fbf8ef;border:1px solid #f1e9d5;border-radius:8px;color:#8d774e;font-size:11px;line-height:1.7}.fw-field-nav{display:flex;align-items:center;justify-content:space-between;margin-top:28px;border-top:1px solid var(--fw-line);padding-top:16px;color:var(--fw-muted);font-size:10px}.fw-inspector-bottom{border-top:1px solid var(--fw-line);padding:14px 20px;background:#fcfbfd}.fw-inspector-bottom .fw-button{width:100%}.fw-inspector-empty{display:flex;align-items:center;justify-content:center;gap:12px;flex-direction:column;text-align:center;color:var(--fw-muted);padding:40px 22px;flex:1;font-size:12px}.fw-review-list{padding:0 20px 18px;max-height:185px;overflow:auto}.fw-review-row{width:100%;border:0;background:transparent;display:flex;align-items:center;gap:8px;text-align:left;padding:7px 0;font-size:10px;color:var(--fw-muted)}.fw-review-row span:nth-child(2){flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fw-review-row-active{color:var(--fw-plum);font-weight:600}.fw-job{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 23px;background:var(--fw-plum-soft);border-bottom:1px solid #dfd3e4;font-size:12px}.fw-job small{color:var(--fw-muted);font-size:10px;display:block;margin-top:2px}.fw-modal-backdrop{position:absolute;inset:0;background:#211a2d66;backdrop-filter:blur(3px);z-index:20;display:flex;align-items:center;justify-content:center;padding:28px}.fw-modal{width:min(590px,100%);max-height:90%;display:flex;flex-direction:column;background:var(--fw-surface);border:1px solid #e9e1ec;border-radius:17px;box-shadow:0 20px 100px #170c2840;overflow:hidden}.fw-modal-head{display:flex;align-items:flex-start;justify-content:space-between;padding:24px 25px 18px;gap:15px;border-bottom:1px solid var(--fw-line)}.fw-modal h2{font-family:Georgia,'Times New Roman',serif;font-size:27px;font-weight:400;letter-spacing:-.7px}.fw-modal-sub{font-size:12px;color:var(--fw-muted);margin-top:7px!important}.fw-modal-body{padding:20px 25px;overflow:auto}.fw-modal-foot{border-top:1px solid var(--fw-line);padding:15px 25px;display:flex;gap:10px;align-items:center;justify-content:space-between;background:#fcfbfd}.fw-picker-path{display:flex;gap:8px;align-items:center;margin-bottom:15px;color:var(--fw-muted);font-size:11px;overflow-wrap:anywhere}.fw-picker-files{border:1px solid var(--fw-line);border-radius:10px;overflow:hidden}.fw-picker-file{display:flex;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--fw-line);cursor:pointer;font-size:12px}.fw-picker-file:last-child{border-bottom:0}.fw-picker-file:hover{background:#f8f5fa}.fw-picker-file span{flex:1;overflow-wrap:anywhere}.fw-picker-folder{width:100%;text-align:left;background:white;border:0;border-bottom:1px solid var(--fw-line);color:var(--fw-plum)}.fw-picker-empty{padding:26px;color:var(--fw-muted);text-align:center;font-size:12px}.fw-confirm{display:flex;gap:10px;align-items:flex-start;font-size:12px;line-height:1.6;margin-top:17px}.fw-confirm input{margin-top:3px}.fw-summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:4px 0 22px}.fw-summary-card{padding:15px;background:#f6f3f8;border:1px solid #eae2ef;border-radius:9px}.fw-summary-card strong{display:block;font-family:Georgia,'Times New Roman',serif;font-size:27px;font-weight:400;line-height:1.3;color:var(--fw-plum)}.fw-summary-card span{font-size:10px;color:var(--fw-muted)}.fw-export-file{display:flex;align-items:center;gap:12px;border:1px solid var(--fw-line);padding:14px;border-radius:10px;margin-top:9px}.fw-export-file>div{min-width:0;flex:1}.fw-export-file strong{font-size:12px;font-weight:550;overflow-wrap:anywhere}.fw-export-file small{display:block;color:var(--fw-muted);font-size:10px;margin-top:3px}.fw-success-seal{width:53px;height:53px;border-radius:50%;display:grid;place-items:center;background:var(--fw-green-soft);color:var(--fw-green);margin-bottom:15px}.fw-evidence-modal{width:min(900px,100%)}.fw-evidence-layout{display:grid;grid-template-columns:1fr 260px;min-height:0;overflow:auto}.fw-evidence-image{padding:22px;background:#efebf1;overflow:auto}.fw-evidence-image img{width:100%;display:block;box-shadow:0 2px 12px #24142b15}.fw-evidence-copy{padding:22px;border-left:1px solid var(--fw-line)}.fw-propagate-row{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--fw-line);border-radius:9px;padding:12px;margin-top:9px}.fw-propagate-row strong{font-size:12px;font-weight:550;display:block}.fw-propagate-row small{font-size:10px;color:var(--fw-muted);display:block;margin-top:4px}.fw-scrollbar::-webkit-scrollbar{width:6px;height:6px}.fw-scrollbar::-webkit-scrollbar-thumb{background:#d4cbd8;border-radius:10px}.fw-live{padding:50px;color:var(--fw-muted);display:grid;place-items:center;flex:1}.fw-mobile-selector{display:none}.fw{position:relative}.fw-screen-reader{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
@keyframes fw-spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.fw *{transition:none!important;animation:none!important}}@media(max-width:1150px){.fw-body{grid-template-columns:170px minmax(230px,1fr) 260px}.fw-top{padding:16px 20px}.fw-steps{display:none}.fw-rail{padding:18px 8px}.fw-canvas{padding:20px}.fw-inspector-body{padding:18px 16px}.fw-inspector-head{padding:19px 16px}.fw-empty-inner{gap:25px}}@media(max-width:880px){.fw-body{grid-template-columns:minmax(240px,1fr) 270px}.fw-rail{display:none}.fw-mobile-selector{display:block;max-width:220px;border:1px solid var(--fw-line);border-radius:7px;background:white;padding:5px;font-size:11px}.fw-doc-top h2{display:none}.fw-doc-top{padding:13px 16px}.fw-top .fw-tagline{display:none}.fw-empty-inner{grid-template-columns:1fr}.fw-illustration{display:none}.fw-empty-inner{min-height:unset}.fw-empty{padding-top:35px}.fw-features{gap:14px}.fw-modal-backdrop{padding:18px}}@media(max-width:620px){.fw-body{display:flex;flex-direction:column;overflow:auto}.fw-main{min-height:360px;flex:1 0 360px}.fw-inspector{border-left:0;border-top:1px solid var(--fw-line);flex:0 0 auto;overflow:visible}.fw-inspector-body{padding-bottom:16px}.fw-top-actions .fw-button{font-size:11px;padding:7px 9px;min-height:32px}.fw-top{padding:13px 16px;gap:10px}.fw-wordmark{font-size:18px}.fw-logo{width:32px;height:32px;border-radius:10px}.fw-top-actions .fw-refresh{display:none}.fw-features{grid-template-columns:1fr}.fw-modal-backdrop{padding:10px}.fw-evidence-layout{grid-template-columns:1fr}.fw-evidence-copy{border-left:0;border-top:1px solid var(--fw-line)}.fw-review-list{display:none}.fw-bottom span:last-child{display:none}}
@media(prefers-color-scheme:dark){.fw{--fw-paper:#201e25;--fw-surface:#28252d;--fw-ink:#ede8ee;--fw-muted:#afa4b4;--fw-line:#403847;--fw-plum:#a986b7;--fw-plum-soft:#3a2e42;--fw-green:#8fc5aa;--fw-green-soft:#263e33;--fw-amber:#dec18c;--fw-amber-soft:#403625}.fw-top,.fw-doc-top,.fw-toolbar,.fw-bottom{background:var(--fw-surface)}.fw-rail{background:#242028}.fw-doc-active{background:#312a36!important;border-color:#594762}.fw-button:not(.fw-primary){background:#302a36}.fw-quiet{background:transparent!important}.fw-primary{background:#9670a7;color:#fff;border-color:#9670a7}.fw-quote,.fw-input,.fw-modal-foot,.fw-inspector-bottom,.fw-picker-folder{background:#302a36;color:var(--fw-ink)}.fw-pill{background:#3b3341;color:var(--fw-muted)}.fw-pill-green{background:var(--fw-green-soft);color:var(--fw-green)}.fw-pill-amber{background:var(--fw-amber-soft);color:var(--fw-amber)}.fw-pill-plum{background:var(--fw-plum-soft);color:#cab0d6}.fw-canvas{background-color:#1c1920;background-image:radial-gradient(#413747 .65px,transparent .65px)}.fw-step-num{background:#302a36}.fw-progress-ring span{background:var(--fw-surface)}.fw-doc:hover,.fw-rail-source:hover,.fw-picker-file:hover{background:#39313f}.fw-summary-card{background:#362c3d;border-color:#4e3b59}.fw-evidence-image{background:#1e1a23}.fw-no-evidence{background:#3d3425;border-color:#51442e;color:#d5bc8d}.fw-error{background:#482d2d;border-color:#6d4141;color:#efb6a5}.fw-job{border-color:#51405e}.fw-segmented{background:#342b3a}.fw-segmented button[aria-pressed=true]{background:#51405e;color:#e0c9eb}.fw-mobile-selector{background:#302a36;color:var(--fw-ink)}}
`

function Formwork({ ctx }) {
  const profile = SDK.useValue(host.state.profile)
  const [packet, setPacket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [formId, setFormId] = useState('')
  const [fieldId, setFieldId] = useState('')
  const [page, setPage] = useState(1)
  const [missingOnly, setMissingOnly] = useState(false)
  const [draft, setDraft] = useState('')
  const [alternative, setAlternative] = useState(null)
  const [preview, setPreview] = useState(null)
  const [previewError, setPreviewError] = useState('')
  const [modal, setModal] = useState(null)
  const [folder, setFolder] = useState(null)
  const [folderPath, setFolderPath] = useState('')
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState([])
  const [pickerLoading, setPickerLoading] = useState(false)
  const [job, setJob] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [includeSources, setIncludeSources] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [evidenceZoom, setEvidenceZoom] = useState(1)
  const [batchSelected, setBatchSelected] = useState([])
  const [evidencePreview, setEvidencePreview] = useState(null)
  const [evidenceError, setEvidenceError] = useState('')
  const [propagation, setPropagation] = useState(null)
  const [propagatingIds, setPropagatingIds] = useState([])
  const [download, setDownload] = useState(null)
  const mounted = useRef(true)
  const epochRef = useRef(getEpoch())
  const jobTimer = useRef(null)
  const jobGeneration = useRef(0)
  const inputRef = useRef(null)
  const dialogRef = useRef(null)
  const requestSeq = useRef(0)
  const request = async (path, opts) => {
    const epoch = getEpoch()
    if (epochRef.current !== epoch) throw new Error('The connected Hermes profile changed. Please wait for the current packet to open.')
    const result = await ctx.rest(path, opts)
    if (!mounted.current || epoch !== getEpoch()) throw new Error('The connected Hermes profile changed. Please retry in the current profile.')
    if (result?.error) throw new Error(errorText(result.error))
    return result
  }
  const load = async (initial = false) => {
    const sequence = ++requestSeq.current
    try {
      if (initial) setLoading(true)
      const save = typeof SDK.captureGatewayFileDownload === 'function' ? SDK.captureGatewayFileDownload() : null
      const data = await request('/packet')
      if (sequence !== requestSeq.current) return
      setPacket(data.packet || data)
      setDownload(() => save)
    } catch (err) { if (sequence === requestSeq.current && mounted.current) setError(errorText(err)) }
    finally { if (sequence === requestSeq.current && mounted.current) setLoading(false) }
  }

  useEffect(() => {
    mounted.current = true
    epochRef.current = getEpoch()
    setPacket(null); setFormId(''); setFieldId(''); setModal(null); setJob(null); setError(''); setBusy(''); setPreview(null)
    load(true)
    const timer = setInterval(() => {
      if (epochRef.current !== getEpoch()) {
        epochRef.current = getEpoch()
        setPacket(null); setFormId(''); setFieldId(''); setModal(null); setJob(null); setError(''); setBusy(''); setPreview(null)
        load(true)
      }
    }, 1000)
    return () => { mounted.current = false; clearInterval(timer); clearTimeout(jobTimer.current); requestSeq.current++ }
  }, [profile])

  const forms = packet?.forms || []
  const sources = packet?.sources || []
  const activeForm = forms.find(form => form.id === formId) || forms[0]
  const fields = activeForm?.fields || []
  const allFields = useMemo(() => forms.flatMap(form => (form.fields || []).map(field => ({ ...field, formId: form.id, formName: form.name }))), [packet])
  const needsReview = field => field.origin !== 'user' || (field.required && !nonempty(field.value))
  const filteredFields = missingOnly ? fields.filter(needsReview) : fields
  const activeField = fields.find(field => field.id === fieldId) || filteredFields[0] || fields[0]
  const activeEvidence = alternative?.evidence || activeField?.evidence
  const reviewed = allFields.filter(field => field.origin === 'user' && (!field.required || nonempty(field.value))).length
  const missing = allFields.filter(field => field.required && !nonempty(field.value)).length
  const suggested = allFields.filter(field => field.origin === 'model').length
  const pageCount = activeForm?.pageCount || activeForm?.pages?.length || 1
  const pageSpec = activeForm?.pages?.find(item => item.number === page) || activeForm?.pages?.[page - 1] || {}
  const pageFields = fields.filter(field => Number(field.page || 1) === Number(page))
  const attentionCount = fields.filter(needsReview).length
  const progress = fields.length ? Math.round(fields.filter(field => field.origin === 'user' && (!field.required || nonempty(field.value))).length / fields.length * 100) : 0

  useEffect(() => {
    if (!activeForm) return
    if (activeForm.id !== formId) setFormId(activeForm.id)
    if (activeField && activeField.id !== fieldId) setFieldId(activeField.id)
  }, [packet, formId, fieldId, missingOnly])
  useEffect(() => {
    if (!activeField) return
    setDraft(activeField.type === 'checkbox' ? !!activeField.value : text(activeField.value))
    setAlternative(null)
    setPage(Number(activeField.page || 1))
  }, [activeForm?.id, activeField?.id, activeField?.value])
  useEffect(() => {
    let cancelled = false
    if (!activeForm) return
    setPreview(null); setPreviewError('')
    request(`/render?formId=${encodeURIComponent(activeForm.id)}&page=${page}`).then(result => {
      if (!cancelled) setPreview(result)
    }).catch(err => { if (!cancelled) setPreviewError(errorText(err)) })
    return () => { cancelled = true }
  }, [activeForm?.id, page, packet?.revision, packet?.updatedAt, fields.map(field => text(field.value)).join('\u0000')])
  useEffect(() => {
    if (modal?.kind !== 'evidence') return
    let cancelled = false
    const source = modal.source
    setEvidencePreview(null); setEvidenceError('')
    request(`/render?sourceId=${encodeURIComponent(source.id)}&page=${modal.page || 1}`).then(result => { if (!cancelled) setEvidencePreview(result) }).catch(err => { if (!cancelled) setEvidenceError(errorText(err)) })
    return () => { cancelled = true }
  }, [modal?.kind, modal?.source?.id, modal?.page])

  const chooseField = field => { setFieldId(field.id); setPage(Number(field.page || 1)) }
  const navigateField = direction => {
    const list = filteredFields.length ? filteredFields : fields
    const index = list.findIndex(field => field.id === activeField?.id)
    if (list.length) chooseField(list[(index + direction + list.length) % list.length])
  }
  const chooseForm = id => { setFormId(id); setFieldId(''); setPage(1) }
  const runAction = async (title, action) => {
    if (busy) return
    setBusy(title); setError('')
    try { await action() } catch (err) { if (mounted.current) setError(errorText(err)) }
    finally { if (mounted.current) setBusy('') }
  }
  const listFolder = async (chosen, path = '') => {
    setPickerLoading(true)
    try {
      const result = await ctx.files.list(chosen.id, path)
      if (!result.ok) throw new Error(result.message || 'This folder could not be opened.')
      setEntries((result.entries || []).filter(entry => entry.isDirectory || /\.pdf$/i.test(entry.name)).sort((a,b) => Number(b.isDirectory) - Number(a.isDirectory) || a.name.localeCompare(b.name)))
      setFolder(chosen); setFolderPath(path); setSelected([])
      if (result.truncated) setError('This folder has too many entries. Choose a smaller folder to see every document.')
    } finally { setPickerLoading(false) }
  }
  const pickFolder = () => runAction('Choosing documents', async () => {
    if (!ctx.files?.requestFolder || !ctx.files?.readDataUrl) throw new Error('This Hermes Desktop version does not provide document folder access. Update Hermes Desktop and try again.')
    const result = await ctx.files.requestFolder()
    if (!result.ok) throw new Error(result.message || 'Folder access is unavailable.')
    if (!result.folder) return
    await listFolder(result.folder)
    setModal({ kind: 'picker' })
  })
  const importFiles = () => runAction('Adding your documents', async () => {
    if (!selected.length) return
    const files = []
    for (const entry of selected) {
      const result = await ctx.files.readDataUrl(folder.id, entry.path || [folderPath, entry.name].filter(Boolean).join('/'))
      if (!result.ok) throw new Error(`${entry.name}: ${result.message || 'The file could not be read. Each PDF must be under 16 MiB.'}`)
      const data = result.url || result.dataUrl
      if (!data || !data.includes(',')) throw new Error(`${entry.name}: Desktop did not return readable document data.`)
      files.push({ name: entry.name, data: data.slice(data.indexOf(',') + 1) })
    }
    await request('/upload', { method: 'POST', body: { files } })
    setModal(null); setSelected([])
    await load()
  })
  const pollJob = async (jobId, epoch, generation) => {
    if (!mounted.current || epoch !== getEpoch() || generation !== jobGeneration.current) return
    try {
      const result = await request(`/jobs/${encodeURIComponent(jobId)}`)
      if (generation !== jobGeneration.current) return
      if (['done', 'completed', 'complete', 'succeeded', 'success'].includes(result.status)) {
        setJob(null)
        await load()
        return
      }
      if (['failed', 'error', 'cancelled'].includes(result.status)) throw new Error(errorText(result.error || result.message || 'The model could not finish reading these documents. Your existing values are unchanged.'))
      setJob({ ...result, jobId })
      jobTimer.current = setTimeout(() => pollJob(jobId, epoch, generation), 1500)
    } catch (err) { if (mounted.current && epoch === getEpoch()) { setJob(null); setError(errorText(err)) } }
  }
  const extract = () => runAction('Starting suggestions', async () => {
    const epoch = getEpoch()
    if (epochRef.current !== epoch) throw new Error('The connected Hermes profile changed. Please wait for the current packet to open.')
    const result = await host.request('plugin.formwork.extract', {})
    if (!mounted.current || epoch !== getEpoch()) throw new Error('The connected Hermes profile changed. Please retry in the current profile.')
    if (!result.jobId) throw new Error('The extraction service did not return a job ID. No suggestions have been assumed.')
    setJob(result)
    pollJob(result.jobId, epoch, ++jobGeneration.current)
  })
  const saveValue = (next = false) => runAction('Saving field', async () => {
    if (!activeField || !activeForm) return
    const current = { ...activeField, value: draft, formId: activeForm.id }
    const evidence = alternative?.evidence || activeField.evidence || {}
    const update = { formId: activeForm.id, fieldId: activeField.id, value: draft, origin: 'user' }
    const retainsEvidence = text(draft) === text(activeField.value) || (alternative && text(draft) === text(alternative.value))
    if (retainsEvidence && evidence.sourceId) Object.assign(update, { sourceId: evidence.sourceId, page: evidence.page, quote: evidence.quote })
    await request('/values', { method: 'POST', body: { updates: [update] } })
    const key = sourceKey(activeField.label || activeField.name)
    const matches = key.length > 2 ? allFields.filter(field => field.id !== activeField.id || field.formId !== activeForm.id).filter(field => field.type === activeField.type && !field.readOnly && sourceKey(field.label || field.name) === key && text(field.value) !== text(draft)) : []
    await load()
    if (nonempty(draft) && matches.length) {
      setPropagation({ value: draft, fields: matches, label: label(activeField), evidence: retainsEvidence ? evidence : null })
      setPropagatingIds(matches.map(field => `${field.formId}:${field.id}`))
      setModal({ kind: 'propagate' })
    } else if (next) {
      const index = fields.findIndex(field => field.id === current.id)
      const list = fields.slice(index + 1).concat(fields.slice(0, index)).filter(field => !missingOnly || needsReview(field))
      if (list[0]) chooseField(list[0])
    }
  })
  const propagate = () => runAction('Updating matching fields', async () => {
    const updates = propagation.fields.filter(field => propagatingIds.includes(`${field.formId}:${field.id}`)).map(field => ({ formId: field.formId, fieldId: field.id, value: propagation.value, origin: 'user', ...(propagation.evidence || {}) }))
    if (updates.length) await request('/values', { method: 'POST', body: { updates } })
    setModal(null); setPropagation(null); await load()
  })
  const reviewSuggestions = () => {
    setBatchSelected(allFields.filter(field => field.origin === 'model' && field.evidence?.sourceId && field.evidence?.quote).map(field => `${field.formId}:${field.id}`))
    setConfirmed(false)
    setModal({ kind: 'batch' })
  }
  const approveSuggestions = () => runAction('Approving reviewed answers', async () => {
    const updates = allFields.filter(field => field.origin === 'model' && batchSelected.includes(`${field.formId}:${field.id}`)).map(field => ({ formId: field.formId, fieldId: field.id, value: field.value, origin: 'user', sourceId: field.evidence.sourceId, page: field.evidence.page, quote: field.evidence.quote }))
    if (updates.length) await request('/values', { method: 'POST', body: { updates } })
    setModal(null); setConfirmed(false); await load()
  })
  const exportPacket = () => runAction('Preparing your packet', async () => {
    const result = await request('/export', { method: 'POST', body: { includeSources } })
    await load()
    setModal({ kind: 'download', exports: result.exports || [], warnings: result.warnings || [], includeSources: result.includeSources })
  })
  const newPacket = () => runAction('Starting a fresh packet', async () => {
    await request('/new', { method: 'POST', body: { archiveCurrent: true } })
    jobGeneration.current++
    clearTimeout(jobTimer.current)
    setJob(null); setFormId(''); setFieldId(''); setPage(1); setPreview(null); setMissingOnly(false)
    setAlternative(null); setPropagation(null); setModal(null); setConfirmed(false); setIncludeSources(false)
    await load()
  })
  const showEvidence = (sourceId, evidence = {}) => {
    const source = sources.find(item => item.id === sourceId)
    if (!source) { setError('This source is no longer in the packet. Add it again before relying on this evidence.'); return }
    setEvidenceZoom(1)
    setModal({ kind: 'evidence', source, ...evidence })
  }
  useEffect(() => {
    if (!modal) return
    const previousFocus = document.activeElement
    const timer = setTimeout(() => dialogRef.current?.querySelector('button:not([disabled]),input:not([disabled]),select:not([disabled])')?.focus(), 20)
    const trap = event => {
      if (event.key !== 'Tab' || !dialogRef.current) return
      const items = Array.from(dialogRef.current.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]')).filter(item => item.getClientRects().length)
      if (!items.length) return
      const first = items[0], last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', trap)
    return () => { clearTimeout(timer); document.removeEventListener('keydown', trap); if (previousFocus?.isConnected) previousFocus.focus() }
  }, [modal?.kind])
  useEffect(() => {
    const handler = event => {
      if (modal || !activeField) return
      if (event.altKey && (event.key === 'ArrowDown' || event.key === 'ArrowRight')) { event.preventDefault(); navigateField(1) }
      if (event.altKey && (event.key === 'ArrowUp' || event.key === 'ArrowLeft')) { event.preventDefault(); navigateField(-1) }
      if (event.key === 'Enter' && event.target === inputRef.current && !event.shiftKey && !activeField.multiline && activeField.type !== 'textarea') { event.preventDefault(); saveValue(true) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [activeField, draft, modal, fields, busy, missingOnly])

  const renderValueInput = () => {
    const props = { id: 'fw-field-value', ref: inputRef, className: 'fw-input', value: draft, onChange: event => { setDraft(event.target.value); setAlternative(null) }, disabled: !!busy || activeField.readOnly, autoComplete: 'off', spellCheck: false }
    if (activeField.type === 'checkbox') return h('label', { className: 'fw-checkbox-value' }, h('input', { ref: inputRef, type: 'checkbox', checked: !!draft, onChange: event => setDraft(event.target.checked), disabled: !!busy || activeField.readOnly }), valueLabel(activeField, draft))
    if ((activeField.choices || []).length) return h('select', props, h('option', { value: '' }, 'Choose an answer'), ...activeField.choices.map(option => h('option', { key: option.value ?? option, value: option.value ?? option }, option.label ?? option)))
    if (activeField.multiline || activeField.type === 'textarea') return h('textarea', { ...props, className: 'fw-input fw-input-area', rows: 3 })
    return h('input', { ...props, type: 'text', placeholder: 'Enter the missing answer' })
  }

  const renderEmpty = () => h('div', { className: 'fw-empty fw-scrollbar' },
    h('div', { className: 'fw-empty-inner' },
      h('div', null, h('div', { className: 'fw-kicker' }, 'A little less paperwork'), h('h1', null, 'Bring the form.', h('br'), 'Leave with it filled.'), h('p', { className: 'fw-empty-lead' }, 'Your documents already have the answers. Let Hermes find them, show you the evidence, and fill the original PDF.'), h(Button, { primary: true, icon: 'folder', onClick: pickFolder, disabled: !!busy }, 'Choose your documents'), h('small', null, 'Fillable PDFs + supporting PDFs. Your originals stay untouched.')),
      h('div', { className: 'fw-illustration', 'aria-hidden': true }, h('div', { className: 'fw-paper-card fw-paper-card-back' }), h('div', { className: 'fw-paper-card' }, h('div', { className: 'fw-paper-head' }), h('div', { className: 'fw-paper-line' }), h('div', { className: 'fw-paper-line', style: { width: '62%' } }), h('div', { className: 'fw-paper-field' }), h('div', { className: 'fw-paper-field' }), h('div', { className: 'fw-paper-field' }), h('div', { className: 'fw-paper-line', style: { width: '50%', marginTop: 24 } })), h('div', { className: 'fw-check-stamp' }, h(Icon, { name: 'check', size: 30 })))),
    h('div', { className: 'fw-features' }, ...[
      ['link', 'Every answer has a source', 'Review the exact page and quote behind a suggestion.'],
      ['search', 'Only the missing questions', 'Answer what your documents cannot. Never invent a fact.'],
      ['shield', 'The original, finished', 'Export filled PDFs and a clear review record.'],
    ].map(([icon, title, body]) => h('div', { className: 'fw-feature', key: title }, h(Icon, { name: icon, size: 20 }), h('div', null, h('strong', null, title), h('p', null, body))))))

  const renderRail = () => h('aside', { className: 'fw-rail fw-scrollbar', 'aria-label': 'Packet documents' }, h('div', { className: 'fw-rail-heading' }, h('span', { className: 'fw-kicker' }, 'Forms to finish'), h(Pill, null, forms.length)),
    ...forms.map(form => {
      const count = (form.fields || []).filter(needsReview).length
      return h('button', { type: 'button', key: form.id, className: `fw-doc ${activeForm?.id === form.id ? 'fw-doc-active' : ''}`, onClick: () => chooseForm(form.id), 'aria-current': activeForm?.id === form.id ? 'page' : undefined }, h('span', { className: 'fw-doc-icon' }, h(Icon, { size: 17 })), h('span', { className: 'fw-doc-copy' }, h('span', { className: 'fw-doc-name' }, form.name), h('span', { className: 'fw-doc-meta' }, h('span', { className: `fw-dot ${count ? 'fw-dot-amber' : 'fw-dot-green'}` }), count ? `${count} to review` : 'Reviewed')))
    }),
    h('div', { className: 'fw-rail-sources' }, h('div', { className: 'fw-rail-heading' }, h('span', { className: 'fw-kicker' }, 'Supporting documents'), h(Pill, null, sources.length)), ...sources.map(source => h('button', { type: 'button', className: 'fw-rail-source', key: source.id, onClick: () => showEvidence(source.id) }, h(Icon, { size: 15 }), h('span', null, source.name))), !sources.length && h('p', { className: 'fw-rail-note' }, 'Add supporting PDFs so Hermes can find grounded answers.')),
    h('p', { className: 'fw-rail-note' }, 'Suggestions use the Formwork extraction model in Hermes. Original files are never overwritten.'))

  const renderDocument = () => h('section', { className: 'fw-main', 'aria-label': 'Original form preview' },
    h('div', { className: 'fw-doc-top' }, h('div', null, h('div', { className: 'fw-kicker' }, 'The original form'), h('h2', null, activeForm?.name), h('select', { className: 'fw-mobile-selector', value: activeForm?.id || '', onChange: event => chooseForm(event.target.value), 'aria-label': 'Choose form' }, ...forms.map(form => h('option', { key: form.id, value: form.id }, form.name)))), h('div', { className: 'fw-progress-ring', style: { '--fw-progress': progress }, 'aria-label': `${progress}% of fields reviewed` }, h('span', null, `${progress}%`))),
    h('div', { className: 'fw-toolbar' }, h('div', { className: 'fw-segmented', 'aria-label': 'Fields to review' }, h('button', { type: 'button', 'aria-pressed': !missingOnly, onClick: () => setMissingOnly(false) }, 'All fields'), h('button', { type: 'button', 'aria-pressed': missingOnly, onClick: () => setMissingOnly(true) }, `To review · ${attentionCount}`)), h('div', { className: 'fw-page-control' }, h(Button, { quiet: true, className: 'fw-icon-button', icon: 'left', 'aria-label': 'Previous page', disabled: page <= 1, onClick: () => setPage(page - 1) }), h('span', null, `${page} / ${pageCount}`), h('select', { className: 'fw-zoom', value: zoom, onChange: event => setZoom(Number(event.target.value)), 'aria-label': 'Form zoom' }, ...[[1, 'Fit'], [1.25, '125%'], [1.5, '150%'], [2, '200%']].map(([value, name]) => h('option', { value, key: value }, name))), h(Button, { quiet: true, className: 'fw-icon-button', icon: 'right', 'aria-label': 'Next page', disabled: page >= pageCount, onClick: () => setPage(page + 1) }))),
    h('div', { className: 'fw-canvas fw-scrollbar' }, preview?.dataUrl ? h('div', { className: 'fw-sheet', style: { width: `${zoom * 100}%`, maxWidth: `${780 * zoom}px` } }, h('img', { src: preview.dataUrl, alt: `${activeForm.name}, page ${page}` }), ...pageFields.filter(field => !missingOnly || needsReview(field) || field.id === activeField?.id).map(field => {
      const rect = field.rect || field.display_rect
      const width = pageSpec.width || preview.width
      const height = pageSpec.height || preview.height
      if (!rect || !width || !height) return null
      return h('button', { type: 'button', key: field.id, className: `fw-field-overlay ${field.id === activeField?.id ? 'fw-field-overlay-active' : ''} ${field.origin === 'user' && !needsReview(field) ? 'fw-field-overlay-reviewed' : !nonempty(field.value) ? 'fw-field-overlay-missing' : ''}`, style: { left: `${rect[0] / width * 100}%`, top: `${rect[1] / height * 100}%`, width: `${(rect[2] - rect[0]) / width * 100}%`, height: `${(rect[3] - rect[1]) / height * 100}%` }, onClick: () => chooseField(field), title: `${label(field)}${field.required ? ' (required)' : ''}: ${valueLabel(field)}`, 'aria-label': `Review ${label(field)}${field.required ? ', required' : ''}` }, field.id === activeField?.id && h('span', { className: 'fw-field-overlay-label' }, label(field)))
    })) : h('div', { className: 'fw-render-state' }, previewError ? h(Icon, { name: 'alert', size: 26 }) : h(Spinner, null, 'Opening your form'), previewError && h('p', null, previewError))),
    h('div', { className: 'fw-bottom' }, h('span', null, h('span', { className: 'fw-dot fw-dot-amber' }), ' Needs an answer', '  ·  ', h('span', { className: 'fw-dot fw-dot-green' }), ' Reviewed'), h('span', null, h('kbd', null, 'Alt'), ' + ', h('kbd', null, '↓'), ' Next field')))

  const renderConflict = () => activeField?.status === 'conflict' && h('div', { style: { marginBottom: 18 } },
    h('div', { className: 'fw-no-evidence', style: { marginBottom: 12 } }, 'The documents disagree. Choose the right answer, or enter one you can confirm.'),
    ...(activeField.alternatives || []).map((item, index) => h('button', { type: 'button', key: index, onClick: () => { setAlternative(item); setDraft(item.value) }, disabled: !!busy, className: 'fw-batch-item', style: { width: '100%', textAlign: 'left', background: alternative === item ? 'var(--fw-plum-soft)' : 'var(--fw-surface)', color: 'var(--fw-ink)', cursor: 'pointer' } }, h('strong', null, text(item.value)), h('blockquote', { className: 'fw-quote' }, item.evidence?.quote || 'No supporting excerpt'), h('small', null, sources.find(source => source.id === item.evidence?.sourceId)?.name || 'Source document', ` · page ${item.evidence?.page || 1}`))))

  const renderInspector = () => h('aside', { className: 'fw-inspector fw-scrollbar', 'aria-label': 'Field review' },
    h('div', { className: 'fw-inspector-head' }, h('span', { className: 'fw-kicker' }, 'Review an answer'), h(Pill, { tone: attentionCount ? 'amber' : 'green' }, `${attentionCount} left`)),
    activeField ? h('div', { className: 'fw-inspector-body' }, h(Pill, { tone: activeField.origin === 'user' ? 'green' : nonempty(activeField.value) ? 'plum' : 'amber' }, activeField.origin === 'user' ? 'Reviewed by you' : activeField.status === 'conflict' ? 'Conflicting sources' : nonempty(activeField.value) ? 'Suggested answer' : activeField.required ? 'Required · missing' : 'No answer yet'), h('h3', { className: 'fw-field-title' }, label(activeField)), activeField.readOnly && h(Pill, null, 'Read only in the original'), renderConflict(), h('label', { className: 'fw-label', htmlFor: 'fw-field-value' }, activeField.type === 'checkbox' ? 'Your answer' : 'Value in the form'), renderValueInput(), h(Button, { primary: true, icon: 'check', className: 'fw-save', disabled: !!busy || !!job, onClick: () => saveValue(true) }, busy === 'Saving field' ? 'Saving…' : 'Save & next'),
      h('div', { className: 'fw-evidence' }, h('div', { className: 'fw-evidence-title' }, h(Icon, { name: 'link', size: 14 }), 'Where this came from'), activeEvidence?.quote ? h('div', null, h('blockquote', { className: 'fw-quote' }, activeEvidence.quote), h('button', { type: 'button', className: 'fw-source-button', onClick: () => showEvidence(activeEvidence.sourceId, activeEvidence) }, h(Icon, { size: 13 }), h('span', null, sources.find(source => source.id === activeEvidence.sourceId)?.name || 'Source document', ` · page ${activeEvidence.page || 1}`), h(Icon, { name: 'right', size: 12 }))) : h('div', { className: 'fw-no-evidence' }, activeField.origin === 'user' ? 'This answer was provided or confirmed by you.' : 'No supporting evidence yet. Enter an answer you know, or add a document that contains it.')),
      h('div', { className: 'fw-field-nav' }, h(Button, { quiet: true, className: 'fw-icon-button', icon: 'left', onClick: () => navigateField(-1), 'aria-label': 'Previous field' }), h('span', null, `${Math.max(0, (filteredFields.length ? filteredFields : fields).findIndex(field => field.id === activeField.id)) + 1} of ${filteredFields.length || fields.length} fields`), h(Button, { quiet: true, className: 'fw-icon-button', icon: 'right', onClick: () => navigateField(1), 'aria-label': 'Next field' }))) : h('div', { className: 'fw-inspector-empty' }, h(Icon, { name: 'check', size: 30 }), h('p', null, 'Choose a highlighted field on the form to review its answer.')),
    h('div', { className: 'fw-review-list fw-scrollbar' }, h('div', { className: 'fw-kicker', style: { marginBottom: 8 } }, 'On this form'), ...filteredFields.map(field => h('button', { type: 'button', className: `fw-review-row ${field.id === activeField?.id ? 'fw-review-row-active' : ''}`, key: field.id, onClick: () => chooseField(field) }, h('span', { className: `fw-dot ${field.origin === 'user' ? 'fw-dot-green' : 'fw-dot-amber'}` }), h('span', null, label(field)), field.required && !nonempty(field.value) && h('span', null, 'Required')))),
    h('div', { className: 'fw-inspector-bottom' }, suggested > 0 && h(Button, { primary: true, icon: 'check', disabled: !!busy || !!job, onClick: reviewSuggestions, style: { marginBottom: 9 } }, `Review ${suggested} suggestion${suggested === 1 ? '' : 's'}`), h(Button, { icon: 'spark', disabled: !!busy || !!job || !sources.length, onClick: extract }, job ? 'Reading documents…' : 'Find answers in documents'), !sources.length && h('p', { className: 'fw-tiny fw-muted', style: { marginTop: 8 } }, 'Add a supporting PDF to suggest answers.')))

  const renderModal = () => {
    if (!modal) return null
    const close = () => { if (!busy) { setModal(null); setConfirmed(false) } }
    let title = '', sub = '', body = null, foot = null, extraClass = ''
    if (modal.kind === 'new') {
      title = 'Start a fresh packet?'; sub = 'Keep the current work, and make room for the next task.'
      body = h('div', null, h('p', { className: 'fw-muted', style: { lineHeight: 1.8 } }, `Your current ${forms.length} form${forms.length === 1 ? '' : 's'} and ${sources.length} supporting document${sources.length === 1 ? '' : 's'} will be archived on this Hermes profile. Imported originals and exports stay saved. The workspace will open empty.`), job && h('div', { className: 'fw-note', style: { marginTop: 15 } }, 'The current extraction will not apply its results to the new packet.'))
      foot = h('div', { className: 'fw-modal-foot' }, h(Button, { quiet: true, onClick: close, disabled: !!busy }, 'Keep working'), h(Button, { primary: true, icon: 'folder', onClick: newPacket, disabled: !!busy }, busy ? 'Archiving…' : 'Archive & start new'))
    } else if (modal.kind === 'picker') {
      title = 'Your paperwork, together.'; sub = 'Select the blank form and the PDFs that hold its answers.'
      body = h('div', null, h('div', { className: 'fw-picker-path' }, h(Icon, { name: 'folder', size: 15 }), h('span', null, folder?.name, folderPath ? ` / ${folderPath}` : ''), folderPath && h(Button, { quiet: true, className: 'fw-icon-button', icon: 'left', 'aria-label': 'Parent folder', onClick: () => listFolder(folder, folderPath.split('/').slice(0,-1).join('/')).catch(err => setError(errorText(err))) })), pickerLoading ? h(Spinner, null, 'Opening folder') : h('div', { className: 'fw-picker-files' }, ...entries.map(entry => entry.isDirectory ? h('button', { key: entry.path || entry.name, type: 'button', className: 'fw-picker-file fw-picker-folder', onClick: () => listFolder(folder, entry.path || [folderPath, entry.name].filter(Boolean).join('/')).catch(err => setError(errorText(err))) }, h(Icon, { name: 'folder', size: 18 }), h('span', null, entry.name), h(Icon, { name: 'right', size: 15 })) : h('label', { key: entry.path || entry.name, className: 'fw-picker-file' }, h('input', { type: 'checkbox', checked: selected.some(item => item.path === entry.path && item.name === entry.name), onChange: event => setSelected(event.target.checked ? [...selected, entry] : selected.filter(item => !(item.path === entry.path && item.name === entry.name))) }), h(Icon, { size: 18 }), h('span', null, entry.name), h(Pill, null, 'PDF'))), !entries.length && h('p', { className: 'fw-picker-empty' }, 'No PDFs in this folder. Choose another folder.')), h('p', { className: 'fw-tiny fw-muted', style: { marginTop: 14 } }, 'Fillable PDFs become forms. Other PDFs become supporting documents. Originals are read only.'))
      foot = h('div', { className: 'fw-modal-foot' }, h(Button, { quiet: true, onClick: pickFolder, disabled: !!busy }, 'Change folder'), h(Button, { primary: true, icon: 'plus', onClick: importFiles, disabled: !selected.length || !!busy }, busy === 'Adding your documents' ? 'Adding documents…' : `Add ${selected.length || ''} document${selected.length === 1 ? '' : 's'}`))
    } else if (modal.kind === 'export') {
      title = 'A final look. Then, finished.'; sub = 'Export creates new files. Your original PDFs stay untouched.'
      body = h('div', null, h('div', { className: 'fw-summary-grid' }, ...[[forms.length, 'forms'], [reviewed, 'answers reviewed'], [sources.length, 'supporting PDFs']].map(([count, name]) => h('div', { className: 'fw-summary-card', key: name }, h('strong', null, count), h('span', null, name)))), (missing > 0 || suggested > 0) && h('div', { className: 'fw-no-evidence' }, missing > 0 && h('p', null, `${missing} required field${missing === 1 ? ' is' : 's are'} still blank.`), suggested > 0 && h('p', null, `${suggested} suggested answer${suggested === 1 ? ' has' : 's have'} not been individually confirmed.`), h('p', { style: { marginTop: 7 } }, 'Review these fields before treating the packet as complete.')), sources.length > 0 && h('label', { className: 'fw-confirm' }, h('input', { type: 'checkbox', checked: includeSources, onChange: event => setIncludeSources(event.target.checked) }), h('span', null, 'Include the supporting PDFs in the ZIP', h('small', { className: 'fw-muted', style: { display: 'block', fontSize: 10, marginTop: 3 } }, 'Adds the original source files, unchanged.'))), h('label', { className: 'fw-confirm' }, h('input', { type: 'checkbox', checked: confirmed, onChange: event => setConfirmed(event.target.checked) }), h('span', null, 'I have reviewed the values and understand that the PDFs are not signed or submitted.')))
      foot = h('div', { className: 'fw-modal-foot' }, h(Button, { quiet: true, onClick: close, disabled: !!busy }, 'Keep reviewing'), h(Button, { primary: true, icon: 'down', onClick: exportPacket, disabled: !confirmed || !!busy || missing > 0 || suggested > 0 }, busy ? 'Preparing…' : 'Create filled PDFs'))
    } else if (modal.kind === 'download') {
      title = 'Your packet is ready.'; sub = modal.includeSources ? 'Filled originals, supporting PDFs, and a clear record of the reviewed answers.' : 'Filled originals and a clear record of the reviewed answers.'
      const exports = modal.exports.length ? modal.exports : packet?.exports || []
      body = h('div', null, h('div', { className: 'fw-success-seal' }, h(Icon, { name: 'check', size: 27 })), ...(modal.warnings || []).map((warning, i) => h('div', { className: 'fw-no-evidence', key: i, style: { marginBottom: 12 } }, text(warning))), ...exports.map(file => h('div', { className: 'fw-export-file', key: file.path || file.name }, h(Icon, { name: /zip$/i.test(file.name) ? 'folder' : 'file', size: 23 }), h('div', null, h('strong', null, file.name), h('small', null, file.size ? `${Math.ceil(file.size / 1024)} KB` : 'Saved on your Hermes backend')), h(Button, { icon: 'down', 'aria-label': `Download ${file.name}`, onClick: () => download ? download(file.path || file.storedPath, file.name) : setError('Update Hermes Desktop to enable native downloads.'), disabled: !download || !(file.path || file.storedPath) }))), !exports.length && h('p', { className: 'fw-muted' }, 'The backend did not return any export files. Refresh and try again.'))
      foot = h('div', { className: 'fw-modal-foot' }, h('span', { className: 'fw-tiny fw-muted' }, 'Review once more before sending.'), h(Button, { primary: true, onClick: close }, 'Back to the forms'))
    } else if (modal.kind === 'evidence') {
      title = modal.source.name; sub = `Source document · page ${modal.page || 1}`; extraClass = 'fw-evidence-modal'
      body = h('div', { className: 'fw-evidence-layout' }, h('div', { className: 'fw-evidence-image' }, evidencePreview?.dataUrl ? h('img', { style: { width: `${evidenceZoom * 100}%`, maxWidth: 'none' }, src: evidencePreview.dataUrl, alt: `${modal.source.name}, page ${modal.page || 1}` }) : h('div', { className: 'fw-render-state' }, evidenceError ? h('p', null, evidenceError) : h(Spinner, null, 'Opening the source'))), h('div', { className: 'fw-evidence-copy' }, h('div', { className: 'fw-kicker', style: { marginBottom: 14 } }, modal.quote ? 'The cited passage' : 'Source text'), h('blockquote', { className: 'fw-quote' }, modal.quote || (modal.source.textByPage || []).find(item => item.page === (modal.page || 1))?.text || 'Inspect the original page. No text excerpt is available.'), h('p', { className: 'fw-tiny fw-muted', style: { marginTop: 14 } }, 'A citation links a proposed answer to its source. You decide whether the evidence supports that answer.')))
      foot = h('div', { className: 'fw-modal-foot' }, h('div', { className: 'fw-page-control' }, h(Button, { quiet: true, icon: 'left', disabled: (modal.page || 1) <= 1, onClick: () => setModal({ ...modal, page: (modal.page || 1) - 1, quote: '' }), 'aria-label': 'Previous source page' }), h('span', null, `${modal.page || 1} / ${modal.source.pageCount || 1}`), h('select', { className: 'fw-zoom', value: evidenceZoom, onChange: event => setEvidenceZoom(Number(event.target.value)), 'aria-label': 'Source zoom' }, ...[[1, 'Fit'], [1.5, '150%'], [2, '200%']].map(([value, name]) => h('option', { value, key: value }, name))), h(Button, { quiet: true, icon: 'right', disabled: (modal.page || 1) >= (modal.source.pageCount || 1), onClick: () => setModal({ ...modal, page: (modal.page || 1) + 1, quote: '' }), 'aria-label': 'Next source page' })), h(Button, { primary: true, onClick: close }, 'Back to the form'))
    } else if (modal.kind === 'batch') {
      title = 'The answers, with the evidence.'; sub = 'Read the proposed values and their cited passages. Approve only the answers you trust.'; extraClass = 'fw-batch-modal'
      const proposals = allFields.filter(field => field.origin === 'model')
      body = h('div', null, ...proposals.map(field => {
        const key = `${field.formId}:${field.id}`
        const grounded = !!(field.evidence?.sourceId && field.evidence?.quote)
        return h('label', { className: 'fw-batch-item', key }, h('div', { className: 'fw-batch-item-head' }, h('input', { type: 'checkbox', checked: batchSelected.includes(key), disabled: !grounded || !!busy, onChange: event => setBatchSelected(event.target.checked ? [...batchSelected, key] : batchSelected.filter(item => item !== key)) }), h('div', null, h('strong', null, label(field)), h('small', null, field.formName), h('div', { className: 'fw-batch-value' }, typeof field.value === 'boolean' ? field.value ? 'Checked' : 'Unchecked' : text(field.value)), grounded ? h('div', null, h('blockquote', { className: 'fw-quote' }, field.evidence.quote), h('small', null, sources.find(source => source.id === field.evidence.sourceId)?.name || 'Source document', ` · page ${field.evidence.page || 1}`)) : h('div', { className: 'fw-no-evidence' }, 'No supporting citation. Review this field individually.'))))
      }), h('label', { className: 'fw-confirm' }, h('input', { type: 'checkbox', checked: confirmed, onChange: event => setConfirmed(event.target.checked), disabled: !!busy }), h('span', null, 'I reviewed the selected answers and their cited evidence.')))
      foot = h('div', { className: 'fw-modal-foot' }, h(Button, { quiet: true, onClick: close, disabled: !!busy }, 'Review individually'), h(Button, { primary: true, icon: 'check', onClick: approveSuggestions, disabled: !confirmed || !batchSelected.length || !!busy }, busy ? 'Approving…' : `Approve ${batchSelected.length} sourced answer${batchSelected.length === 1 ? '' : 's'}`))
    } else if (modal.kind === 'propagate' && propagation) {
      title = 'Same answer, another form?'; sub = `You confirmed “${propagation.label}”. Choose where else to use it.`
      body = h('div', null, h('div', { className: 'fw-note' }, h(Icon, { name: 'copy', size: 17 }), h('span', null, text(propagation.value))), ...propagation.fields.map(field => { const key = `${field.formId}:${field.id}`; return h('label', { className: 'fw-propagate-row', key }, h('input', { type: 'checkbox', checked: propagatingIds.includes(key), onChange: event => setPropagatingIds(event.target.checked ? [...propagatingIds, key] : propagatingIds.filter(item => item !== key)) }), h('span', null, h('strong', null, label(field)), h('small', null, field.formName), h('small', null, field.value !== null && field.value !== undefined && field.value !== '' ? `Replaces: ${valueLabel(field)}` : 'Currently blank'))) }), h('p', { className: 'fw-tiny fw-muted', style: { marginTop: 15 } }, 'Only fields with the same label are suggested. Check that each one refers to the same person or fact.'))
      foot = h('div', { className: 'fw-modal-foot' }, h(Button, { quiet: true, onClick: close, disabled: !!busy }, 'Only this field'), h(Button, { primary: true, icon: 'check', onClick: propagate, disabled: !propagatingIds.length || !!busy }, busy ? 'Updating…' : `Update ${propagatingIds.length} field${propagatingIds.length === 1 ? '' : 's'}`))
    }
    return h('div', { className: 'fw-modal-backdrop', onClick: event => { if (event.target === event.currentTarget) close() } }, h('section', { ref: dialogRef, className: `fw-modal ${extraClass}`, role: 'dialog', 'aria-modal': true, 'aria-labelledby': 'fw-modal-title', onKeyDown: event => { if (event.key === 'Escape') close() } }, h('div', { className: 'fw-modal-head' }, h('div', null, h('h2', { id: 'fw-modal-title' }, title), h('p', { className: 'fw-modal-sub' }, sub)), h(Button, { quiet: true, icon: 'close', className: 'fw-icon-button', 'aria-label': 'Close dialog', onClick: close, disabled: !!busy })), h('div', { className: modal.kind === 'evidence' ? 'fw-modal-evidence-body' : 'fw-modal-body' }, error && h('div', { className: 'fw-error', role: 'alert', style: { borderRadius: 8, marginBottom: 14 } }, h(Icon, { name: 'alert', size: 17 }), h('span', null, error)), body), foot))
  }

  return h('div', { className: 'fw' }, h('style', null, CSS),
    h('header', { className: 'fw-top' }, h('div', { className: 'fw-brand' }, h('div', { className: 'fw-logo' }, h(Icon, { name: 'file', size: 22 })), h('div', null, h('div', { className: 'fw-wordmark' }, 'Formwork'), h('div', { className: 'fw-tagline' }, 'The answers were already there.'))), h('nav', { className: 'fw-steps', 'aria-label': 'Packet progress' }, ...[['Add documents', forms.length ? 'done' : 'active'], ['Review answers', forms.length ? 'active' : ''], ['Export packet', '']].flatMap(([name, state], i) => [i > 0 && h('span', { className: 'fw-step-line', key: `line-${i}` }), h('span', { className: `fw-step ${state && `fw-step-${state}`}`, key: name }, h('span', { className: 'fw-step-num' }, state === 'done' ? h(Icon, { name: 'check', size: 12 }) : i + 1), name)])), forms.length > 0 && h('div', { className: 'fw-top-actions' }, h(Button, { quiet: true, icon: 'folder', onClick: () => { setError(''); setModal({ kind: 'new' }) }, disabled: !!busy }, 'New packet'), h(Button, { quiet: true, className: 'fw-refresh fw-icon-button', icon: 'refresh', onClick: () => load(), disabled: !!busy, 'aria-label': 'Refresh packet' }), h(Button, { icon: 'plus', onClick: pickFolder, disabled: !!busy || !!job }, 'Add documents'), h(Button, { primary: true, icon: 'down', onClick: () => { setConfirmed(false); setIncludeSources(false); setModal({ kind: 'export' }) }, disabled: !!busy || !!job }, 'Export packet'))),
    error && !modal && h('div', { className: 'fw-error', role: 'alert' }, h(Icon, { name: 'alert', size: 17 }), h('span', null, error), h(Button, { quiet: true, className: 'fw-icon-button', icon: 'close', onClick: () => setError(''), 'aria-label': 'Dismiss error' })),
    job && h('div', { className: 'fw-job', 'aria-live': 'polite' }, h('div', null, h(Spinner, null, 'Hermes is finding the answers'), h('small', null, 'Your Formwork extraction model reads the supporting documents. You review every suggestion.')), h(Pill, { tone: 'plum' }, 'Reading documents')),
    loading ? h('div', { className: 'fw-live' }, h(Spinner, null, 'Opening Formwork')) : forms.length ? h('div', { className: 'fw-body' }, renderRail(), renderDocument(), renderInspector()) : renderEmpty(),
    renderModal())
}

export default {
  id: ID,
  name: 'Formwork',
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: SDK.ROUTES_AREA, data: { path: PATH }, render: () => h(Formwork, { ctx }) },
      { id: 'nav', area: SDK.SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Formwork', codicon: 'files' }, order: 65 },
    ])
  },
}
