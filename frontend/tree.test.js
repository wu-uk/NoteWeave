const assert = require("node:assert/strict");
const { collectNodeIds, filterTreeByQuery } = require("./tree.js");

const tree = {
  id: 1,
  title: "Data Structures",
  path: "Data Structures",
  type: "course_root",
  children: [
    {
      id: 2,
      title: "Sorting",
      path: "Data Structures / Sorting",
      type: "chapter",
      children: [
        {
          id: 3,
          title: "Quick Sort",
          path: "Data Structures / Sorting / Quick Sort",
          type: "knowledge_point",
          children: []
        }
      ]
    },
    {
      id: 4,
      title: "Graphs",
      path: "Data Structures / Graphs",
      type: "chapter",
      children: []
    }
  ]
};

assert.deepEqual(collectNodeIds(tree), [1, 2, 3, 4]);

const quick = filterTreeByQuery(tree, "quick");
assert.deepEqual(quick.matchedIds, [3]);
assert.equal(quick.tree.id, 1);
assert.deepEqual(collectNodeIds(quick.tree), [1, 2, 3]);

const sorting = filterTreeByQuery(tree, "sorting");
assert.deepEqual(sorting.matchedIds, [2, 3]);
assert.deepEqual(collectNodeIds(sorting.tree), [1, 2, 3]);

const none = filterTreeByQuery(tree, "dynamic programming");
assert.equal(none.tree, null);
assert.deepEqual(none.matchedIds, []);
