import * as fs from 'node:fs';
import { copyFile, cp, mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { Command } from '@p67-cli/Command.ts';
import { ctx } from '@p67-cli/context';
import { projectConfig } from '@p67-cli/middleware/project-config';
import { pythonSdkFiles } from '@p67-cli/workspace/Workspace';
import { zipSync } from 'fflate';

// Runner platform config — embedded at compile time.
// Single source of truth shared with the Dockerfile and Makefile.
import runnerPlatformPath from '../../../../containers/runner/runner-platform.json' with {
    type: 'file',
};

interface RunnerPlatform {
    python_version: string;
    pip_platform: string;
    pip_implementation: string;
    docker_platform: string;
}

function getRunnerPlatform(): RunnerPlatform {
    // Bun's `with { type: 'file' }` returns a file path string at runtime,
    // but TypeScript sees it as the parsed JSON type. Cast to string for fs.
    return JSON.parse(
        fs.readFileSync(runnerPlatformPath as unknown as string, 'utf-8'),
    );
}

async function extractLangGraph(
    entrypoint: string,
    buildDir: string,
    projectDir: string,
): Promise<void> {
    const outputPath = path.join(buildDir, 'graph.json');
    const runnerPath = path.join(projectDir, '__extract_graph_runner.mjs');

    const runnerCode = `
import * as fs from 'node:fs';

function toTitleCase(s) {
    return s.replace(/[-_]/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase());
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
try { lgMod = await import('@langchain/langgraph'); } catch {
    console.log('⊘ No LangGraph found, skipping graph extraction');
    process.exit(0);
}

const { StateGraph } = lgMod;
if (!StateGraph?.prototype?.compile) {
    console.log('⊘ StateGraph.compile not found, skipping');
    process.exit(0);
}

const captured = [];
const orig = StateGraph.prototype.compile;
StateGraph.prototype.compile = function(...args) {
    const c = orig.apply(this, args);
    captured.push(c);
    return c;
};

try { await import(${JSON.stringify(entrypoint)}); } catch (e) {
    console.warn('⊘ Graph extraction skipped: ' + (e?.message || e));
    process.exit(0);
} finally {
    StateGraph.prototype.compile = orig;
}

if (!captured.length) {
    console.log('⊘ No LangGraph compile() detected, skipping');
    process.exit(0);
}

const graph = captured[captured.length - 1].getGraph();
const nodes = [];
const edges = [];

for (const [id, node] of Object.entries(graph.nodes)) {
    nodes.push({ id: mapNodeId(id), type: mapNodeType(id), name: mapNodeName(id, node) });
}
let ei = 0;
for (const edge of graph.edges) {
    ei++;
    const e = { id: 'e' + ei, from_node: mapNodeId(edge.source), to_node: mapNodeId(edge.target) };
    if (edge.data && edge.conditional) e.label = edge.data;
    edges.push(e);
}

const result = { name: 'Workflow', description: 'Auto-extracted from LangGraph', nodes, edges };
fs.writeFileSync(${JSON.stringify(outputPath)}, JSON.stringify(result, null, 2));
console.log('✔︎ Extracted graph to ' + ${JSON.stringify(outputPath)});
`;

    fs.writeFileSync(runnerPath, runnerCode);

    try {
        const proc = Bun.spawn(['bun', 'run', runnerPath], {
            stdout: 'inherit',
            stderr: 'inherit',
            cwd: projectDir,
        });
        await proc.exited;
    } finally {
        if (fs.existsSync(runnerPath)) {
            fs.unlinkSync(runnerPath);
        }
    }
}

async function extractLangGraphPython(
    entrypoint: string,
    buildDir: string,
    projectDir: string,
): Promise<void> {
    const reqPath = path.join(projectDir, 'requirements.txt');
    if (!fs.existsSync(reqPath)) return;
    const reqContent = fs.readFileSync(reqPath, 'utf-8');
    if (!reqContent.match(/langgraph/i)) return;

    console.log('Extracting LangGraph topology (Python)...');

    const outputPath = path.join(buildDir, 'graph.json');
    const scriptPath = path.join(projectDir, '__extract_graph.py');
    const venvDir = path.join(projectDir, '__extract_venv');

    const scriptCode = `
import sys, json, os, importlib.util

entrypoint = ${JSON.stringify(entrypoint)}
output_path = ${JSON.stringify(outputPath)}

sys.path.insert(0, os.path.dirname(os.path.abspath(entrypoint)))

try:
    from langgraph.graph import StateGraph
except ImportError:
    print('No langgraph found, skipping')
    sys.exit(0)

captured = []
orig_compile = StateGraph.compile

def patched_compile(self, *args, **kwargs):
    c = orig_compile(self, *args, **kwargs)
    captured.append(c)
    return c

StateGraph.compile = patched_compile

try:
    spec = importlib.util.spec_from_file_location("workflow", entrypoint)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as e:
    print(f"Graph extraction skipped: {e}")
    sys.exit(0)
finally:
    StateGraph.compile = orig_compile

if not captured:
    print('No LangGraph compile() detected, skipping')
    sys.exit(0)

graph = captured[-1].get_graph()

def map_id(nid):
    if nid == '__start__': return 'start'
    if nid == '__end__': return 'end'
    return nid

def map_type(nid):
    if nid in ('__start__', 'start'): return 'start_node'
    if nid in ('__end__', 'end'): return 'end_node'
    return 'action_node'

def map_name(nid, node):
    if nid == '__start__': return 'Start'
    if nid == '__end__': return 'End'
    name = getattr(node, 'name', nid)
    if name and name != nid: return name
    return nid.replace('_', ' ').replace('-', ' ').title()

nodes = [{'id': map_id(nid), 'type': map_type(nid), 'name': map_name(nid, node)}
         for nid, node in graph.nodes.items()]

edges = []
for i, edge in enumerate(graph.edges, 1):
    e = {'id': f'e{i}', 'from_node': map_id(edge.source), 'to_node': map_id(edge.target)}
    if edge.data and edge.conditional:
        e['label'] = edge.data
    edges.append(e)

result = {'name': 'Workflow', 'description': 'Auto-extracted from LangGraph', 'nodes': nodes, 'edges': edges}
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f'Extracted graph to {output_path} - nodes: {len(nodes)} edges: {len(edges)}')
`;

    fs.writeFileSync(scriptPath, scriptCode);

    try {
        const venvResult = Bun.spawnSync(['python3', '-m', 'venv', venvDir], {
            cwd: projectDir,
            stdout: 'inherit',
            stderr: 'inherit',
        });
        if (venvResult.exitCode !== 0) {
            console.warn(
                '⚠ Failed to create venv for graph extraction, skipping',
            );
            return;
        }

        const pip = path.join(venvDir, 'bin', 'pip');
        Bun.spawnSync([pip, 'install', '-q', '-r', reqPath], {
            cwd: projectDir,
            stdout: 'inherit',
            stderr: 'inherit',
        });

        const python = path.join(venvDir, 'bin', 'python');
        const proc = Bun.spawn([python, scriptPath], {
            stdout: 'inherit',
            stderr: 'inherit',
            cwd: projectDir,
        });
        await proc.exited;
    } finally {
        if (fs.existsSync(scriptPath)) fs.unlinkSync(scriptPath);
        if (fs.existsSync(venvDir))
            fs.rmSync(venvDir, { recursive: true, force: true });
    }
}

async function buildTypeScript(
    entrypoint: string,
    buildDir: string,
): Promise<void> {
    const result = await Bun.build({
        entrypoints: [entrypoint],
        target: 'node',
        format: 'esm',
        outdir: buildDir,
        sourcemap: true,
    });

    if (result.success && result.outputs.length) {
        for (const output of result.outputs) {
            console.log(`✔︎ Created ${output.path}`);
        }
    }
}

async function buildPython(
    projectDir: string,
    buildDir: string,
): Promise<void> {
    // Copy src/ directory to build/
    const srcDir = path.join(projectDir, 'src');
    if (fs.existsSync(srcDir)) {
        await cp(srcDir, buildDir, { recursive: true });
        console.log(`✔︎ Copied src/ to ${buildDir}`);
    } else {
        throw new Error(`Source directory not found: ${srcDir}`);
    }

    // Copy requirements.txt if it exists, then vendor dependencies
    const requirementsSrc = path.join(projectDir, 'requirements.txt');
    if (fs.existsSync(requirementsSrc)) {
        const requirementsDest = path.join(buildDir, 'requirements.txt');
        await copyFile(requirementsSrc, requirementsDest);
        console.log(`✔︎ Copied requirements.txt to ${buildDir}`);

        // Vendor dependencies into build dir (analogous to esbuild bundling for TS).
        // Uses --platform and --python-version to download pre-built wheels
        // matching the runner container, regardless of the developer's local machine.
        // All vendored files (including native .so extensions) are included in
        // workflow.zip. The runner unzips them to real filesystem paths, so
        // zipimport limitations don't apply.
        const content = fs.readFileSync(requirementsSrc, 'utf-8');
        const hasPackages = content
            .split('\n')
            .some((line) => line.trim() && !line.trim().startsWith('#'));

        if (hasPackages) {
            const platform = getRunnerPlatform();
            console.log('Installing Python dependencies...');
            const pipResult = Bun.spawnSync(
                [
                    'python3',
                    '-m',
                    'pip',
                    'install',
                    '-r',
                    requirementsSrc,
                    '--target',
                    buildDir,
                    '--platform',
                    platform.pip_platform,
                    '--only-binary=:all:',
                    '--python-version',
                    platform.python_version,
                    '--implementation',
                    platform.pip_implementation,
                    '--no-compile',
                    '-q',
                ],
                { cwd: projectDir, stdout: 'inherit', stderr: 'inherit' },
            );
            if (pipResult.exitCode === 0) {
                console.log('✔︎ Vendored Python dependencies into build');
            } else {
                console.warn(
                    `⚠ pip install failed (exit ${pipResult.exitCode}). Dependencies may be missing at runtime.`,
                );
            }
        }
    }

    // Bundle the p67_sdk package (full implementation) with the workflow.
    // SDK files are embedded in the binary at compile time via Bun's
    // `with { type: 'file' }` imports, so this works from any install location.
    const sdkDestDir = path.join(buildDir, 'p67_sdk');
    await mkdir(sdkDestDir, { recursive: true });
    for (const [ref, filename] of Object.entries(pythonSdkFiles)) {
        const src = await Bun.file(ref).text();
        await Bun.write(path.join(sdkDestDir, filename), src);
    }
    console.log('✔︎ Bundled p67_sdk with workflow');
}

export const buildCommand = new Command('build')
    .description('Build the project')
    .use(projectConfig)
    .action(async () => {
        const config = ctx().projectConfig;
        const { entrypoint, buildDir, projectDir, language } = config;

        console.log(`Building ${language} workflow...`);

        // Clean buildDir if it exists
        if (fs.existsSync(buildDir)) {
            fs.rmSync(buildDir, { recursive: true, force: true });
            console.log(`✔︎ Cleaned ${buildDir}`);
        }

        // Create buildDir
        await mkdir(buildDir, { recursive: true });

        try {
            if (language === 'python') {
                await buildPython(projectDir, buildDir);
            } else {
                await buildTypeScript(entrypoint, buildDir);
            }
        } catch (error) {
            console.error('Build failed:', error);
            throw error;
        }

        // Auto-extract LangGraph topology (no-op if no LangGraph)
        if (language === 'typescript') {
            await extractLangGraph(entrypoint, buildDir, projectDir);
        } else if (language === 'python') {
            await extractLangGraphPython(entrypoint, buildDir, projectDir);
        }

        // Copy manifest.yaml to buildDir
        const manifestSrc = path.join(projectDir, 'manifest.yaml');
        const manifestDest = path.join(buildDir, 'manifest.yaml');

        if (fs.existsSync(manifestSrc)) {
            await copyFile(manifestSrc, manifestDest);
            console.log(`✔︎ Copied manifest.yaml to ${buildDir}`);
        } else {
            console.warn(
                `⚠ manifest.yaml not found in ${projectDir}. Skipping copy.`,
            );
        }

        // Zip buildDir contents into workflow.zip
        const zipPath = path.join(buildDir, 'workflow.zip');
        const files: Record<string, Uint8Array> = {};

        // Read all files from buildDir
        const bundleFiles = fs.readdirSync(buildDir, { recursive: true });
        for (const file of bundleFiles) {
            const filePath = path.join(buildDir, file as string);
            const stat = fs.statSync(filePath);

            if (stat.isFile()) {
                const relativePath = path.relative(buildDir, filePath);
                files[relativePath] = fs.readFileSync(filePath);
            }
        }

        // Create zip
        const zipped = zipSync(files, { level: 9 });
        fs.writeFileSync(zipPath, zipped);
        console.log(`✔︎ Created ${zipPath}`);
    });
