// Conversor de Markdown mínimo para os documentos de QA (sem dependências, funciona offline).
// Suporta: títulos, parágrafos, listas (com marcas, numeradas e checkboxes), tabelas,
// blocos de código, código em linha, negrito, itálico, links e linhas horizontais.
(function () {
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function inline(text) {
    const codes = [];
    let s = text.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
    s = esc(s)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) =>
        /^(https?:\/\/|\/|#|[\w.-]+\.md)/.test(url) ? `<a href="${url}">${label}</a>` : label);
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[+i])}</code>`);
  }

  const cells = row => row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());

  function render(md) {
    const lines = md.replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (/^```/.test(line)) {                                   // bloco de código
        const buf = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        out.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`); i++; continue;
      }
      const h = line.match(/^(#{1,4})\s+(.*)$/);                 // título
      if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }
      if (/^\s*---+\s*$/.test(line)) { out.push("<hr>"); i++; continue; }
      if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {   // tabela
        const head = cells(line), aligns = cells(lines[i + 1]).map(c => /-:$/.test(c) ? "right" : "left");
        i += 2;
        const rows = [];
        while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
        out.push("<table><thead><tr>" + head.map((c, k) => `<th style="text-align:${aligns[k] || "left"}">${inline(c)}</th>`).join("") +
          "</tr></thead><tbody>" + rows.map(r => "<tr>" + r.map((c, k) => `<td style="text-align:${aligns[k] || "left"}">${inline(c)}</td>`).join("") + "</tr>").join("") +
          "</tbody></table>");
        continue;
      }
      if (/^\s*([-*]|\d+\.)\s+/.test(line)) {                    // lista
        const ordered = /^\s*\d+\./.test(line);
        const items = [];
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          let item = lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, "");
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s+/.test(lines[i])) item += " " + lines[i++].trim();
          const task = item.match(/^\[( |x)\]\s+(.*)$/i);
          items.push(task ? `<li><input type="checkbox" disabled ${task[1].toLowerCase() === "x" ? "checked" : ""}>${inline(task[2])}</li>` : `<li>${inline(item)}</li>`);
        }
        out.push(`<${ordered ? "ol" : "ul"}>${items.join("")}</${ordered ? "ol" : "ul"}>`);
        continue;
      }
      if (!line.trim()) { i++; continue; }
      const para = [];                                            // parágrafo
      while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*\||\s*([-*]|\d+\.)\s+)/.test(lines[i])) para.push(lines[i++].trim());
      out.push(`<p>${inline(para.join(" "))}</p>`);
    }
    return out.join("\n");
  }

  window.renderMarkdown = render;
})();
