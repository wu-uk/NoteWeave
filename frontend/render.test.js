const assert = require("node:assert/strict");
const { renderMarkdown, sanitizeUrl } = require("./render.js");

const html = renderMarkdown(`# 标题

正文包含 **重点**、\`code\` 和 $O(n log n)$。

- 列表项

\`\`\`python
print("<safe>")
\`\`\`

![图](/api/files/example.png)

$$
a^2 + b^2 = c^2
$$
`);

assert.match(html, /<h1>标题<\/h1>/);
assert.match(html, /<strong>重点<\/strong>/);
assert.match(html, /<code>code<\/code>/);
assert.match(html, /class="math-inline">O\(n log n\)<\/span>/);
assert.match(html, /<li>列表项<\/li>/);
assert.match(html, /print\(&quot;&lt;safe&gt;&quot;\)/);
assert.match(html, /<img src="\/api\/files\/example.png" alt="图" \/>/);
assert.match(html, /class="math-block">a\^2 \+ b\^2 = c\^2<\/div>/);

const unsafeHtml = renderMarkdown(`<img src=x onerror=alert(1)>
[bad](javascript:alert(1))`);
assert.doesNotMatch(unsafeHtml, /<img src=x/);
assert.doesNotMatch(unsafeHtml, /<a href=/);
assert.doesNotMatch(unsafeHtml, /javascript:/);
assert.match(unsafeHtml, /&lt;img src=x/);
assert.equal(sanitizeUrl("javascript:alert(1)"), "");
assert.equal(sanitizeUrl("/api/files/a.png"), "/api/files/a.png");
