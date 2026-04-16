package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDetectLanguage_GSMode(t *testing.T) {
	dir := t.TempDir()
	// Even with main.py present, GS mode takes priority
	os.WriteFile(filepath.Join(dir, "main.py"), []byte(""), 0644)

	t.Setenv("AUTOMATION_ENTRYPOINT", "my_module:app")

	cmd, args := detectLanguage(dir)

	if cmd != "python3" {
		t.Errorf("expected python3, got %s", cmd)
	}
	if len(args) != 1 || args[0] != "/app/host_gs.py" {
		t.Errorf("expected [/app/host_gs.py], got %v", args)
	}
}

func TestDetectLanguage_GSModeNoWorkflowFiles(t *testing.T) {
	// GS mode doesn't need main.py or index.js — entrypoint comes from env
	dir := t.TempDir()

	t.Setenv("AUTOMATION_ENTRYPOINT", "automations.triage.graph:app")

	cmd, args := detectLanguage(dir)

	if cmd != "python3" {
		t.Errorf("expected python3, got %s", cmd)
	}
	if len(args) != 1 || args[0] != "/app/host_gs.py" {
		t.Errorf("expected [/app/host_gs.py], got %v", args)
	}
}

func TestDetectLanguage_LocalPython(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "main.py"), []byte(""), 0644)

	t.Setenv("AUTOMATION_ENTRYPOINT", "")

	cmd, args := detectLanguage(dir)

	if cmd != "python3" {
		t.Errorf("expected python3, got %s", cmd)
	}
	if len(args) != 1 || args[0] != "/app/host.py" {
		t.Errorf("expected [/app/host.py], got %v", args)
	}
}

func TestDetectLanguage_LocalJS(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "index.js"), []byte(""), 0644)

	t.Setenv("AUTOMATION_ENTRYPOINT", "")

	cmd, args := detectLanguage(dir)

	if cmd != "node" {
		t.Errorf("expected node, got %s", cmd)
	}
	if len(args) != 1 || args[0] != "/app/host.js" {
		t.Errorf("expected [/app/host.js], got %v", args)
	}
}

func TestDetectLanguage_EmptyEntrypointIsNotGSMode(t *testing.T) {
	// Empty string for AUTOMATION_ENTRYPOINT should NOT trigger GS mode
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "main.py"), []byte(""), 0644)

	t.Setenv("AUTOMATION_ENTRYPOINT", "")

	cmd, args := detectLanguage(dir)

	if cmd != "python3" {
		t.Errorf("expected python3, got %s", cmd)
	}
	if args[0] != "/app/host.py" {
		t.Errorf("expected /app/host.py (local mode), got %s", args[0])
	}
}

func TestFileExists(t *testing.T) {
	dir := t.TempDir()

	existingFile := filepath.Join(dir, "exists.txt")
	os.WriteFile(existingFile, []byte("hello"), 0644)

	if !fileExists(existingFile) {
		t.Error("fileExists should return true for existing file")
	}

	if fileExists(filepath.Join(dir, "nope.txt")) {
		t.Error("fileExists should return false for missing file")
	}
}
