(function attachRenderer(root) {
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function sanitizeUrl(value) {
    const url = String(value || "").trim();
    if (!url) return "";
    if (/^(https?:|data:image\/|\/api\/files\/|\.\/|\.\.\/|\/)/i.test(url)) return url;
    return "";
  }

  function tokenStore() {
    const tokens = [];
    return {
      put(html) {
        const token = `\u0000${tokens.length}\u0000`;
        tokens.push(html);
        return token;
      },
      restore(html) {
        return html.replace(/\u0000(\d+)\u0000/g, (_, index) => tokens[Number(index)] || "");
      }
    };
  }

  function renderInline(value) {
    const store = tokenStore();
    let text = String(value || "");
    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
      const safeUrl = sanitizeUrl(url);
      if (!safeUrl) return escapeHtml(alt);
      return store.put(`<img src="${escapeHtml(safeUrl)}" alt="${escapeHtml(alt)}" />`);
    });
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
      const safeUrl = sanitizeUrl(url);
      if (!safeUrl) return escapeHtml(label);
      return store.put(`<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`);
    });
    text = text.replace(/`([^`]+)`/g, (_, code) => store.put(`<code>${escapeHtml(code)}</code>`));
    text = text.replace(/\\\((.+?)\\\)|\$([^$\n]+?)\$/g, (_, parenMath, dollarMath) => {
      const math = parenMath || dollarMath || "";
      return store.put(`<span class="math-inline">${escapeHtml(math)}</span>`);
    });

    let html = escapeHtml(text);
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    return store.restore(html);
  }

  function renderParagraph(lines) {
    return `<p>${renderInline(lines.join("\n")).replace(/\n/g, "<br />")}</p>`;
  }

  function normalizeMindMapLine(line) {
    return line
      .replace(/^\s*[-*]\s+/, "")
      .replace(/^\s+/, "")
      .trim();
  }

  function renderMindMap(source) {
    const rows = String(source || "")
      .replace(/\r\n/g, "\n")
      .split("\n")
      .map((line) => ({
        indent: (line.match(/^\s*/) || [""])[0].replace(/\t/g, "  ").length,
        text: normalizeMindMapLine(line)
      }))
      .filter((row) => row.text);
    if (!rows.length) return "";

    let html = '<div class="mindmap"><ul>';
    const stack = [rows[0].indent];
    rows.forEach((row, index) => {
      if (index === 0) {
        html += `<li><span>${renderInline(row.text)}</span>`;
        return;
      }
      const previous = rows[index - 1];
      if (row.indent > previous.indent) {
        stack.push(row.indent);
        html += "<ul>";
      } else {
        html += "</li>";
        while (stack.length > 1 && row.indent < stack[stack.length - 1]) {
          stack.pop();
          html += "</ul></li>";
        }
      }
      html += `<li><span>${renderInline(row.text)}</span>`;
    });
    while (stack.length > 1) {
      stack.pop();
      html += "</li></ul>";
    }
    html += "</li></ul></div>";
    return html;
  }

  function isBlockStart(line) {
    return /^(#{1,3})\s+/.test(line)
      || /^>\s?/.test(line)
      || /^[-*]\s+/.test(line)
      || /^\d+\.\s+/.test(line)
      || line.trim() === "$$";
  }

  function renderTextBlocks(markdown) {
    const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
    const blocks = [];
    for (let index = 0; index < lines.length;) {
      const line = lines[index];
      if (!line.trim()) {
        index += 1;
        continue;
      }

      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        index += 1;
        continue;
      }

      if (line.trim() === "$$") {
        const mathLines = [];
        index += 1;
        while (index < lines.length && lines[index].trim() !== "$$") {
          mathLines.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) index += 1;
        blocks.push(`<div class="math-block">${escapeHtml(mathLines.join("\n"))}</div>`);
        continue;
      }

      if (/^>\s?/.test(line)) {
        const quoteLines = [];
        while (index < lines.length && /^>\s?/.test(lines[index])) {
          quoteLines.push(lines[index].replace(/^>\s?/, ""));
          index += 1;
        }
        blocks.push(`<blockquote>${renderParagraph(quoteLines)}</blockquote>`);
        continue;
      }

      if (/^[-*]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^[-*]\s+/.test(lines[index])) {
          items.push(`<li>${renderInline(lines[index].replace(/^[-*]\s+/, ""))}</li>`);
          index += 1;
        }
        blocks.push(`<ul>${items.join("")}</ul>`);
        continue;
      }

      if (/^\d+\.\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\d+\.\s+/.test(lines[index])) {
          items.push(`<li>${renderInline(lines[index].replace(/^\d+\.\s+/, ""))}</li>`);
          index += 1;
        }
        blocks.push(`<ol>${items.join("")}</ol>`);
        continue;
      }

      const paragraph = [];
      while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
        paragraph.push(lines[index]);
        index += 1;
      }
      blocks.push(renderParagraph(paragraph));
    }
    return blocks.join("");
  }

  function renderMarkdown(markdown) {
    const parts = [];
    const source = String(markdown || "");
    const fencePattern = /```([a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g;
    let cursor = 0;
    let match;
    while ((match = fencePattern.exec(source)) !== null) {
      parts.push(renderTextBlocks(source.slice(cursor, match.index)));
      const language = (match[1] || "").toLowerCase();
      const body = match[2].replace(/\n$/, "");
      if (language === "mindmap") {
        parts.push(renderMindMap(body));
      } else if (language === "mermaid" && body.trimStart().startsWith("mindmap")) {
        parts.push(renderMindMap(body.replace(/^\s*mindmap\s*\n?/, "")));
      } else {
        const lang = match[1] ? ` language-${escapeHtml(match[1])}` : "";
        parts.push(`<pre><code class="${lang.trim()}">${escapeHtml(body)}</code></pre>`);
      }
      cursor = match.index + match[0].length;
    }
    parts.push(renderTextBlocks(source.slice(cursor)));
    return parts.join("");
  }

  const api = { escapeHtml, renderInline, renderMarkdown, renderMindMap, sanitizeUrl };
  root.NoteWeaveRender = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
