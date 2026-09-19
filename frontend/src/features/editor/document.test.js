import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeImages, importMarkdown } from './document.js';
test('legacy standalone images become blocks without changing fenced code', () => {
  assert.equal(normalizeImages('文字\n![图片](x.jpg)\n说明'),'文字\n\n![图片](x.jpg)\n\n说明');
  const code='```md\n![图片](x.jpg)\n```'; assert.equal(normalizeImages(code),code);
});
test('local image URLs are rebased and existing absolute URLs are retained', () => {
  const blocks=[{props:{url:'keyframes/01.jpg'},children:[{props:{url:'/static/x.png'}}]}];
  const result=importMarkdown({tryParseMarkdownToBlocks:()=>blocks},'', 'frames_test');
  assert.equal(result[0].props.url,'/static/frames_test/keyframes/01.jpg');
  assert.equal(result[0].children[0].props.url,'/static/x.png');
});
