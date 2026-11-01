export function plainText(value) {
  if (typeof DOMParser !== 'undefined') return new DOMParser().parseFromString(String(value || ''), 'text/html').body.textContent.replace(/\s+/g, ' ').trim();
  return String(value || '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}
export function safeSourceURL(value, base) {
  if (typeof value !== 'string' || !value.trim()) return null;
  try {
    const url = new URL(value, base);
    return url.origin === base.origin && url.pathname.startsWith(base.pathname) ? url.href : null;
  } catch { return null; }
}
export function searchDocs(question, index) {
  const stop = new Set(['how','what','when','where','does','can','could','the','with','for','and','are','you','your','kionga']);
  const terms = [...new Set(question.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [])].filter(term => term.length > 2 && !stop.has(term)).map(term => term.length > 4 ? term.replace(/s$/, '') : term);
  const ranked = (index.docs || []).map(doc => ({ ...doc, score: terms.reduce((sum,term) => sum + (String(doc.title).toLowerCase().includes(term) ? 8 : 0) + (plainText(doc.text).toLowerCase().includes(term) ? 1 : 0),0) })).filter(doc => doc.score > 0).sort((a,b) => b.score - a.score);
  const seen = new Set();
  return ranked.filter(doc => { const path = doc.location.split('#')[0]; if (seen.has(path)) return false; seen.add(path); return true; }).slice(0,4);
}
export async function requestAnswer(endpoint, question, page, history, fetcher = fetch) {
  const url = new URL(endpoint, page);
  if (url.protocol !== 'https:' && url.origin !== new URL(page).origin) throw new Error('HTTPS required');
  const response = await fetcher(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, page, history: history.slice(-6) }), signal: AbortSignal.timeout(30000), credentials: 'omit' });
  if (!response.ok) throw new Error('AI unavailable');
  const answer = await response.json();
  if (typeof answer.answer !== 'string' || !answer.answer.trim()) throw new Error('Invalid answer');
  return { answer: answer.answer, sources: Array.isArray(answer.sources) ? answer.sources.slice(0,6) : [] };
}
