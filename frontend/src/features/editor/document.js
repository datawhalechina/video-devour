// Legacy reports sometimes put a standalone image directly after text.
// BlockNote only supports block images, so separate those lines before parsing.
export function normalizeImages(markdown) {
  let fence = null;
  return markdown.split('\n').map(line => {
    const marker = line.match(/^\s*(`{3,}|~{3,})/);
    if (marker) {
      if (!fence) fence = marker[1];
      else if (marker[1][0] === fence[0] && marker[1].length >= fence.length) fence = null;
    }
    return !fence && /^!\[.*\]\(.+\)\s*$/.test(line) ? `\n${line}\n` : line;
  }).join('\n');
}
export function importMarkdown(editor, markdown, outputDir) {
  const blocks = editor.tryParseMarkdownToBlocks(normalizeImages(markdown));
  const visit = (block) => {
    if (block.props?.url && !/^(?:[a-z]+:|\/|#)/i.test(block.props.url)) {
      block.props.url = `/static/${outputDir}/${block.props.url.replace(/^\.\//, '')}`;
    }
    block.children?.forEach(visit);
  };
  blocks.forEach(visit);
  return blocks.length ? blocks : [{ type: 'paragraph' }];
}
export function download(content, name, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
