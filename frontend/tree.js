(function attachTreeHelpers(root) {
  function cloneNode(node, children) {
    return { ...node, children };
  }

  function collectNodeIds(node, ids = []) {
    if (!node) return ids;
    ids.push(node.id);
    (node.children || []).forEach((child) => collectNodeIds(child, ids));
    return ids;
  }

  function filterTreeByQuery(rootNode, query) {
    const normalized = String(query || "").trim().toLowerCase();
    if (!rootNode) return { tree: null, matchedIds: [] };
    if (!normalized) return { tree: rootNode, matchedIds: [] };

    const matchedIds = [];
    function visit(node) {
      const children = node.children || [];
      const haystack = [node.title, node.path, node.type, node.description]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matched = haystack.includes(normalized);
      if (matched) matchedIds.push(node.id);
      const filteredChildren = children.map(visit).filter(Boolean);
      if (!matched && filteredChildren.length === 0) return null;
      return cloneNode(node, matched ? children : filteredChildren);
    }

    return { tree: visit(rootNode), matchedIds };
  }

  const api = { collectNodeIds, filterTreeByQuery };
  root.NoteWeaveTree = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
