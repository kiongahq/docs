/* Optional AI endpoint; without one, the assistant searches the public docs locally. */
(() => {
  const panel = document.getElementById('kg-assistant');
  if (!panel) return;
  const launch = document.getElementById('kg-assistant-launch');
  const input = document.getElementById('kg-question');
  const form = document.getElementById('kg-assistant-form');
  const messages = document.getElementById('kg-messages');
  const submit = form.querySelector('[type="submit"]');
  const indexURL = new URL(panel.dataset.index, location.href);
  const base = new URL('../', indexURL);
  const endpoint = panel.dataset.endpoint;
  const history = [];
  let indexPromise;
  let busy = false;

  function open() {
    if (!panel.open) panel.showModal();
    input.focus();
  }
  launch.addEventListener('click', open);
  document.getElementById('kg-assistant-close').addEventListener('click', () => panel.close());
  panel.addEventListener('close', () => launch.focus());
  document.addEventListener('click', event => {
    if (event.target.closest('[data-ask-kionga]')) open();
  });
  if (endpoint) {
    document.getElementById('kg-assistant-mode').textContent = 'Ask a question about Kionga. AI answers can make mistakes; check the linked documentation.';
    document.getElementById('kg-assistant-notice').textContent = 'AI mode · Questions and recent conversation are sent to the configured service. Do not include secrets.';
  } else {
    document.getElementById('kg-assistant-mode').textContent = 'Search the documentation in your own words. AI answers are not connected yet.';
  }

  function message(text, role = 'assistant') {
    const item = document.createElement('div');
    item.className = `kg-message kg-message--${role}`;
    item.textContent = text;
    messages.append(item);
    item.scrollIntoView({ block: 'nearest' });
    return item;
  }
  function textOnly(html) {
    return new DOMParser().parseFromString(html, 'text/html').body.textContent.replace(/\s+/g, ' ').trim();
  }
  function safeDocURL(value) {
    if (typeof value !== 'string' || !value.trim()) return null;
    const url = new URL(value, base);
    // Links must stay inside the documentation, including when returned by AI.
    return url.origin === base.origin && url.pathname.startsWith(base.pathname) ? url.href : null;
  }
  function sources(item, entries) {
    for (const entry of entries) {
      const href = safeDocURL(entry.location || entry.url);
      if (!href) continue;
      const link = document.createElement('a');
      link.href = href;
      link.textContent = entry.title || 'Read documentation';
      if (entry.text) {
        const snippet = document.createElement('small');
        snippet.textContent = textOnly(entry.text).slice(0, 220);
        link.append(snippet);
      }
      link.addEventListener('click', () => panel.close());
      item.append(link);
    }
  }
  async function search(question) {
    if (!indexPromise) {
      indexPromise = fetch(indexURL, { signal: AbortSignal.timeout(15000) })
        .then(response => {
          if (!response.ok) throw new Error('Search unavailable');
          return response.json();
        }).catch(error => { indexPromise = undefined; throw error; });
    }
    const index = await indexPromise;
    const stop = new Set(['how', 'what', 'when', 'where', 'does', 'can', 'could', 'the', 'with', 'for', 'and', 'are', 'you', 'your', 'kionga']);
    const terms = [...new Set(question.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [])]
      .filter(term => term.length > 2 && !stop.has(term))
      .map(term => term.length > 4 ? term.replace(/s$/, '') : term);
    const ranked = index.docs.map(doc => {
      const title = doc.title.toLowerCase();
      const body = textOnly(doc.text).toLowerCase();
      const score = terms.reduce((sum, term) => sum + (title.includes(term) ? 8 : 0) + (body.includes(term) ? 1 : 0), 0);
      return { ...doc, score };
    }).filter(doc => doc.score > 0).sort((a, b) => b.score - a.score);
    const seen = new Set();
    const results = ranked.filter(doc => {
      const page = doc.location.split('#')[0];
      if (seen.has(page)) return false;
      seen.add(page);
      return true;
    }).slice(0, 4);
    const item = message(results.length ? 'Here are the closest matches in the documentation:' : 'No close matches found. Try a topic such as installation, workspaces, pipelines or agents.');
    sources(item, results);
  }
  async function ask(question) {
    if (busy || !question.trim()) return;
    busy = true;
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    input.value = '';
    message(question, 'user');
    const status = message(endpoint ? 'Looking up an answer…' : 'Searching documentation…');
    try {
      if (endpoint) {
        const url = new URL(endpoint, location.href);
        if (url.protocol !== 'https:' && url.origin !== location.origin) throw new Error('HTTPS required');
        const response = await fetch(url, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, page: location.href, history: history.slice(-6) }),
          signal: AbortSignal.timeout(30000), credentials: 'omit'
        });
        if (!response.ok) throw new Error('AI unavailable');
        const answer = await response.json();
        if (typeof answer.answer !== 'string' || !answer.answer.trim()) throw new Error('Invalid answer');
        status.textContent = answer.answer;
        sources(status, Array.isArray(answer.sources) ? answer.sources.slice(0, 6) : []);
        history.push({ role: 'user', content: question }, { role: 'assistant', content: answer.answer });
        history.splice(0, Math.max(0, history.length - 6));
      } else {
        await search(question);
        status.remove();
      }
    } catch {
      status.textContent = endpoint ? 'The AI service is unavailable. Showing documentation matches instead.' : 'Search could not load. Please use the site search or the navigation menu.';
      if (endpoint) {
        try { await search(question); } catch { message('Documentation search is also unavailable. Please use the navigation menu.'); }
      }
    } finally {
      busy = false;
      submit.disabled = false;
      form.removeAttribute('aria-busy');
      messages.lastElementChild?.scrollIntoView({ block: 'nearest' });
      if (panel.open) input.focus();
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); ask(input.value.trim()); });
  panel.querySelectorAll('.kg-suggestions button').forEach(button => button.addEventListener('click', () => ask(button.textContent)));
})();
