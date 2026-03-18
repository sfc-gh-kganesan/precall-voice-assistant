import * as fs from 'node:fs';
import * as path from 'node:path';

const projectDir = process.argv[2];
if (!projectDir) {
    console.error('Usage: bun /tmp/extract_graph.mjs <project_dir>');
    process.exit(1);
}

process.chdir(projectDir);

const buildDir = path.join(projectDir, 'build');
if (!fs.existsSync(buildDir)) fs.mkdirSync(buildDir, { recursive: true });

function toTitleCase(s) {
    return s.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
function mapNodeId(id) {
    if (id === '__start__') return 'start';
    if (id === '__end__') return 'end';
    return id;
}
function mapNodeType(id) {
    if (id === '__start__' || id === 'start') return 'start_node';
    if (id === '__end__' || id === 'end') return 'end_node';
    return 'action_node';
}
function mapNodeName(id, node) {
    if (id === '__start__') return 'Start';
    if (id === '__end__') return 'End';
    if (node.name && node.name !== id) return node.name;
    return toTitleCase(id);
}

let lgMod;
try {
    lgMod = await import('@langchain/langgraph');
} catch {
    console.log('No LangGraph found, skipping');
    process.exit(0);
}

const { StateGraph } = lgMod;
const captured = [];
const orig = StateGraph.prototype.compile;
StateGraph.prototype.compile = function (...args) {
    const c = orig.apply(this, args);
    captured.push(c);
    return c;
};

try {
    await import('./src/index.ts');
} catch (e) {
    console.warn('Extraction failed:', e?.message || e);
    process.exit(1);
} finally {
    StateGraph.prototype.compile = orig;
}

if (!captured.length) {
    console.log('No graphs captured');
    process.exit(0);
}

const graph = captured[captured.length - 1].getGraph();
const nodes = [];
const edges = [];

for (const [id, node] of Object.entries(graph.nodes)) {
    nodes.push({
        id: mapNodeId(id),
        type: mapNodeType(id),
        name: mapNodeName(id, node),
    });
}
let ei = 0;
for (const edge of graph.edges) {
    ei++;
    const e = {
        id: `e${ei}`,
        from_node: mapNodeId(edge.source),
        to_node: mapNodeId(edge.target),
    };
    if (edge.data && edge.conditional) e.label = edge.data;
    edges.push(e);
}

const outputPath = path.join(buildDir, 'graph.json');
const result = {
    name: 'Workflow',
    description: 'Auto-extracted from LangGraph',
    nodes,
    edges,
};
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
console.log(
    'Extracted graph to',
    outputPath,
    '- nodes:',
    nodes.length,
    'edges:',
    edges.length,
);
