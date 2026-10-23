// Exercise the shipped widget with a small DOM adapter; no browser or network required.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const script = readFileSync('docs/javascripts/assistant.js', 'utf8');

class Element {
  constructor() { this.listeners = {}; this.children = []; this.dataset = {}; this.value = ''; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  append(item) { item.parent = this; this.children.push(item); }
  remove() { this.parent.children = this.parent.children.filter(item => item !== this); }
  setAttribute() {}
  removeAttribute() {}
  scrollIntoView() {}
  focus() { this.focused = true; }
  showModal() { this.open = true; }
  close() { this.open = false; this.listeners.close?.(); }
  querySelector() { return this.submit ||= new Element(); }
  querySelectorAll() { return []; }
  get lastElementChild() { return this.children.at(-1); }
}
function widget({ endpoint = '', fetch } = {}) {
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  get('kg-assistant').dataset = { index: '../../search/search_index.json', endpoint };
  const document = { getElementById: get, createElement: () => new Element(), addEventListener() {} };
  vm.runInNewContext(script, {
    document, location: { href: 'https://example.test/docs/guides/agents/', origin: 'https://example.test' },
    URL, AbortSignal, fetch,
    DOMParser: class { parseFromString(value) { return { body: { textContent: value.replace(/<[^>]*>/g, '') } }; } }
  });
  return {
    get,
    async ask(question) {
      get('kg-question').value = question;
      get('kg-assistant-form').listeners.submit({ preventDefault() {} });
      await new Promise(resolve => setImmediate(resolve));
      return get('kg-messages').children;
    }
  };
}

test('nested pages fetch the root search index and link to distinct matching pages', async () => {
  let requested;
  const app = widget({ fetch: async url => {
    requested = String(url);
    return { ok: true, json: async () => ({ docs: [
      { title: 'Install Kionga', text: '<p>Install on your machine.</p>', location: 'getting-started/installation/' },
      { title: 'Install on Linux', text: 'Install', location: 'getting-started/installation/#linux' },
      { title: 'Agents', text: 'Deploy an agent', location: 'guides/agents/' }
    ] }) };
  } });
  const messages = await app.ask('How do I install Kionga?');
  assert.equal(requested, 'https://example.test/docs/search/search_index.json');
  assert.equal(messages.at(-1).children.length, 1);
  assert.equal(messages.at(-1).children[0].href, 'https://example.test/docs/getting-started/installation/');
  assert.equal(messages.at(-1).children[0].children[0].textContent, 'Install on your machine.');
});

test('AI requests carry context while external and script source links are discarded', async () => {
  let payload;
  const app = widget({ endpoint: 'https://assistant.test/chat', fetch: async (url, options) => {
    payload = JSON.parse(options.body);
    assert.equal(options.credentials, 'omit');
    return { ok: true, json: async () => ({ answer: '<script>untrusted</script>', sources: [
      { title: 'Unsafe', url: 'javascript:alert(1)' },
      { title: 'External', url: 'https://other.test/docs/' },
      { title: 'Outside docs', url: '/admin' },
      { title: 'Missing URL' },
      { title: 'Agents', url: 'guides/agents/' }
    ] }) };
  } });
  const messages = await app.ask('How do I deploy an agent?');
  assert.equal(payload.question, 'How do I deploy an agent?');
  assert.equal(payload.page, 'https://example.test/docs/guides/agents/');
  assert.deepEqual(payload.history, []);
  assert.equal(messages.at(-1).textContent, '<script>untrusted</script>');
  assert.equal(messages.at(-1).children.length, 1);
  assert.equal(messages.at(-1).children[0].href, 'https://example.test/docs/guides/agents/');
});

test('AI failure falls back to search and restores the composer', async () => {
  const app = widget({ endpoint: 'https://assistant.test/chat', fetch: async (url, options) => {
    if (options.method === 'POST') throw new Error('Offline');
    return { ok: true, json: async () => ({ docs: [{ title: 'Pipelines', text: 'Run pipelines', location: 'guides/pipelines/' }] }) };
  } });
  const messages = await app.ask('pipelines');
  assert.match(messages[1].textContent, /AI service is unavailable/);
  assert.equal(messages.at(-1).children[0].href, 'https://example.test/docs/guides/pipelines/');
  assert.equal(app.get('kg-assistant-form').querySelector().disabled, false);
});

test('failed index requests can be retried, and empty matches have useful guidance', async () => {
  let attempts = 0;
  const app = widget({ fetch: async () => {
    if (++attempts === 1) throw new Error('Offline');
    return { ok: true, json: async () => ({ docs: [] }) };
  } });
  let messages = await app.ask('unrelated');
  assert.match(messages.at(-1).textContent, /Search could not load/);
  messages = await app.ask('unrelated');
  assert.match(messages.at(-1).textContent, /No close matches/);
  assert.equal(attempts, 2);
});
