import { test } from 'node:test';
import assert from 'node:assert/strict';
import { searchDocs, safeSourceURL, requestAnswer } from '../ui/src/search.mjs';
const base = new URL('https://example.test/docs/');
test('documentation search ranks titles and deduplicates sections of one page', () => {
 const results=searchDocs('How do I install Kionga?',{docs:[{title:'Install Kionga',text:'Install on your machine.',location:'getting-started/installation/'},{title:'Install on Linux',text:'Install',location:'getting-started/installation/#linux'},{title:'Agents',text:'Deploy an agent',location:'guides/agents/'}]});
 assert.equal(results.length,1);assert.equal(results[0].location,'getting-started/installation/');
});
test('source links remain inside the documentation root',()=>{
 for(const url of ['javascript:alert(1)','https://other.test/docs/','/admin','/docs-evil/',null,''])assert.equal(safeSourceURL(url,base),null);
 assert.equal(safeSourceURL('guides/agents/',base),'https://example.test/docs/guides/agents/');
});
test('AI requests omit credentials and preserve only recent history',async()=>{
 let payload;
 const answer=await requestAnswer('https://assistant.test/chat','How do I deploy an agent?','https://example.test/docs/guides/agents/',Array.from({length:8},(_,i)=>({role:'user',content:String(i)})),async(url,options)=>{payload=JSON.parse(options.body);assert.equal(options.credentials,'omit');return{ok:true,json:async()=>({answer:'<script>untrusted</script>',sources:[{title:'Agents',url:'guides/agents/'}]})}});
 assert.equal(payload.question,'How do I deploy an agent?');assert.equal(payload.history.length,6);assert.equal(answer.answer,'<script>untrusted</script>');
});
test('cross-origin AI endpoints require HTTPS and invalid responses fail',async()=>{
 await assert.rejects(requestAnswer('http://assistant.test/chat','Question','https://example.test/docs/',[],async()=>{throw new Error('should not send')}),/HTTPS/);
 await assert.rejects(requestAnswer('https://assistant.test/chat','Question','https://example.test/docs/',[],async()=>({ok:true,json:async()=>({answer:''})})),/Invalid answer/);
});
