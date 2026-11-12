import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createPortal } from 'react-dom';
import { plainText, requestAnswer, safeSourceURL, searchDocs } from './search.mjs';

type Source = { title?: string; location?: string; url?: string; text?: string };
type Message = { role: 'user' | 'assistant'; text: string; sources?: Source[] };
type Configuration = { site_name: string; version: string; assistant_enabled: boolean; assistant_endpoint: string; product_url: string };
const script = document.querySelector<HTMLScriptElement>('script[src*="javascripts/interface.js"]');
const base = new URL('../', script?.src || window.location.href);
let indexPromise: Promise<any> | undefined;
function Navigation({ config, host }: { config: Configuration; host: Element }) {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    window.addEventListener('popstate', update);
    const subscription = (window as any).document$?.subscribe(update);
    return () => { window.removeEventListener('popstate', update); subscription?.unsubscribe(); };
  }, []);
  const handbook = config.site_name === 'Kionga Engineering';
  const product = handbook ? new URL(config.product_url) : base;
  const links = [
    ['Documentation', product.href, !handbook && !path.includes('/reference/api/') && !path.includes('/changelog/')],
    ['API reference', new URL('reference/api/', product).href, !handbook && path.includes('/reference/api/')],
  ];
  return createPortal(<nav className="kg-wayfinding" aria-label="Documentation sections"><div className="kg-wayfinding-inner md-grid"><div className="kg-wayfinding-links">{links.map(([label, href, active]) => <a key={String(label)} href={String(href)} className={active ? 'kg-wayfinding-active' : undefined} aria-current={active ? 'page' : undefined}>{label}</a>)}</div>{config.version && <span className="kg-version" aria-label={`Documentation version: ${config.version}`}>{config.version}</span>}</div></nav>, host);
}
function ReleaseNotes({ host }: { host: Element }) {
  return createPortal(<a className="kg-release-link" href={new URL('changelog/', base).href}><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3Z"/><path d="M8 7h8M8 11h8M8 15h5"/></svg><span>Release notes</span></a>, host);
}
function Assistant({ config }: { config: Configuration }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const conversation = useRef<{role:string;content:string}[]>([]);
  const panel = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const launch = useRef<HTMLButtonElement>(null);
  const transcript = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open && !panel.current?.open) { panel.current?.showModal(); input.current?.focus(); } else if (!open && panel.current?.open) panel.current.close(); }, [open]);
  useEffect(() => { transcript.current?.lastElementChild?.scrollIntoView({ block: 'nearest' }); }, [messages]);
  useEffect(() => { const click = (event: MouseEvent) => { if ((event.target as Element)?.closest('[data-ask-kionga]')) setOpen(true); }; document.addEventListener('click', click); return () => document.removeEventListener('click', click); }, []);
  async function localSearch(value: string) {
    if (!indexPromise) indexPromise = fetch(new URL('search/search_index.json', base), { signal: AbortSignal.timeout(15000) }).then(response => { if (!response.ok) throw new Error('Search unavailable'); return response.json(); }).catch(error => { indexPromise = undefined; throw error; });
    const sources = searchDocs(value, await indexPromise);
    return { role: 'assistant' as const, text: sources.length ? 'Here are the closest matches in the documentation:' : 'No close matches found. Try installation, workspaces, pipelines or agents.', sources };
  }
  async function ask(value: string) {
    if (busy || !value.trim()) return;
    setBusy(true); setQuestion(''); setMessages(current => [...current, { role: 'user', text: value }]);
    try {
      let answer: Message;
      if (config.assistant_endpoint) {
        try {
          const result = await requestAnswer(config.assistant_endpoint, value, window.location.href, conversation.current);
          answer = { role: 'assistant', text: result.answer, sources: result.sources };
          conversation.current = [...conversation.current, { role: 'user', content: value }, { role: 'assistant', content: result.answer }].slice(-6);
        } catch {
          const matches = await localSearch(value);
          answer = { ...matches, text: `The AI service is unavailable. ${matches.text}` };
        }
      } else answer = await localSearch(value);
      setMessages(current => [...current, answer]);
    } catch { setMessages(current => [...current, { role: 'assistant', text: 'Search could not load. Please use the site search or navigation menu.' }]); }
    finally { setBusy(false); input.current?.focus(); }
  }
  return <><button ref={launch} className="kg-assistant-launch" id="kg-assistant-launch" aria-haspopup="dialog" aria-controls="kg-assistant" onClick={() => setOpen(true)}>Ask Kionga</button><dialog ref={panel} className="kg-assistant" id="kg-assistant" aria-labelledby="kg-assistant-title" onClose={() => { setOpen(false); launch.current?.focus(); }}><header className="kg-assistant-header"><h2 id="kg-assistant-title">Ask Kionga</h2><button type="button" aria-label="Close assistant" onClick={() => setOpen(false)}>Close</button></header><div className="kg-assistant-body"><p id="kg-assistant-mode">{config.assistant_endpoint ? 'Ask a question about Kionga. AI answers can make mistakes; check the linked documentation.' : 'Search the documentation in your own words. AI answers are not connected yet.'}</p><div className="kg-suggestions" aria-label="Suggested questions">{['How do I install Kionga?','How do I deploy an AI agent?','How do pipelines work?'].map(value => <button key={value} type="button" disabled={busy} onClick={() => ask(value)}>{value}</button>)}</div><div ref={transcript} id="kg-messages" role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions">{messages.map((message,index) => <div className={`kg-message kg-message--${message.role}`} key={index}><p>{message.text}</p>{message.sources?.map((source,index) => { const href = safeSourceURL(source.location || source.url, base); return href ? <a key={index} href={href} onClick={() => setOpen(false)}>{source.title || 'Read documentation'}{source.text && <small>{plainText(source.text).slice(0,220)}</small>}</a> : null; })}</div>)}{busy && <p role="status">{config.assistant_endpoint ? 'Looking up an answer…' : 'Searching documentation…'}</p>}</div></div><form id="kg-assistant-form" aria-busy={busy} onSubmit={event => { event.preventDefault(); ask(question.trim()); }}><label htmlFor="kg-question">Your question</label><div className="kg-composer"><input ref={input} id="kg-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={2000} required autoComplete="off" /><button type="submit" disabled={busy}>Send question</button></div><p id="kg-assistant-notice">{config.assistant_endpoint ? 'AI mode. Questions and recent conversation are sent to the configured service. Do not include secrets.' : 'Documentation search. Answers link to the source.'}</p></form></dialog></>;
}
async function mount() {
  const response = await fetch(new URL('javascripts/ui-config.json', base));
  if (!response.ok) return;
  const config: Configuration = await response.json();
  const root = document.createElement('div'); root.id = 'kg-interface-root'; document.body.append(root);
  const nav = document.createElement('div'); nav.id = 'kg-navigation-root';
  const header = document.querySelector('.md-header');
  if (header) header.insertAdjacentElement('afterend', nav); else document.body.prepend(nav);
  const releases = document.createElement('div'); releases.id = 'kg-release-navigation';
  const github = header?.querySelector('.md-header__source');
  if (github) github.insertAdjacentElement('beforebegin', releases);
  else (header?.querySelector('.md-header__inner') || nav).append(releases);
  createRoot(root).render(<><Navigation config={config} host={nav}/><ReleaseNotes host={releases}/>{config.assistant_enabled && <Assistant config={config}/>}</>);
}
void mount().catch(() => {});
