package main

import (
	"os"
	"path/filepath"
)

// detectLanguage inspects the workflow directory and environment to determine
// the appropriate host process.
//
// Detection order:
//  1. GS mode: if AUTOMATION_ENTRYPOINT is set, GS launched this SPCS job
//     directly via the SPCS job spec (no controld, no IPC loop). Always routes
//     to host_gs.py (Python-only in V1). GS mode is checked first so that the
//     local/controld file-based path is completely untouched when running under GS.
//  2. Local/controld mode: inspect the workflow directory for main.py or
//     index.js. This path is only reached when AUTOMATION_ENTRYPOINT is absent,
//     keeping existing controld and local-dev workflows unchanged.
func detectLanguage(workflowDir string) (string, []string) {
	// GS mode — AUTOMATION_ENTRYPOINT is set by GS in the SPCS job spec.
	// This env var contains the Python module:attribute entrypoint from the DPO.
	if os.Getenv("AUTOMATION_ENTRYPOINT") != "" {
		return "python3", []string{"/app/host_gs.py"}
	}

	// Local/controld mode — detect language from workflow files.
	hasPython := fileExists(filepath.Join(workflowDir, "main.py"))
	hasJS := fileExists(filepath.Join(workflowDir, "index.js"))

	switch {
	case hasPython && hasJS:
		fatal("ambiguous workflow: found both main.py and index.js in %s", workflowDir)
	case hasPython:
		return "python3", []string{"/app/host.py"}
	case hasJS:
		return "node", []string{"/app/host.js"}
	default:
		fatal("no workflow entry point found: expected main.py or index.js in %s", workflowDir)
	}
	return "", nil // unreachable
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
