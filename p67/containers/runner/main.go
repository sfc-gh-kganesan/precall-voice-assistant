// p67-runner is a lightweight process supervisor for p67 workflow execution.
//
// It fork-execs the appropriate host process (Python or Node.js) based on the
// workflow contents, then transparently relays stdin/stdout/stderr between the
// orchestrator (controld) and the host.  The Go runner does not parse or
// construct any IPC messages — it is a pure pipe relay.  This gives us a
// single hook point for log capture, timeouts, and resource limits.
//
// Language detection:
//
//	main.py  → python3 /app/host.py
//	index.js → node /app/host.js
//
// Usage:
//
//	p67-runner <workflow-dir>
package main

import (
	"archive/zip"
	"bufio"
	"encoding/base64"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		fatal("usage: p67-runner <workflow-dir>")
	}

	workflowDir := os.Args[1]

	// Validate the workflow directory exists.
	info, err := os.Stat(workflowDir)
	if err != nil || !info.IsDir() {
		fatal("workflow directory does not exist: %s", workflowDir)
	}

	// If the workflow was uploaded as a single zip, extract it before proceeding.
	// This avoids hundreds of individual stage PUT/GET operations.
	zipPath := filepath.Join(workflowDir, "workflow.zip")
	if fileExists(zipPath) {
		fmt.Fprintf(os.Stderr, "[p67-runner] extracting workflow.zip...\n")
		if err := extractZip(zipPath, workflowDir); err != nil {
			fatal("failed to extract workflow.zip: %v", err)
		}
		os.Remove(zipPath) // free disk space
		fmt.Fprintf(os.Stderr, "[p67-runner] extraction complete\n")
	}

	// Detect workflow language and resolve the host command.
	cmdName, cmdArgs := detectLanguage(workflowDir)

	// Start the host process.
	cmd := exec.Command(cmdName, cmdArgs...)
	cmd.Dir = workflowDir

	hostStdin, err := cmd.StdinPipe()
	if err != nil {
		fatal("failed to create stdin pipe: %v", err)
	}

	hostStdout, err := cmd.StdoutPipe()
	if err != nil {
		fatal("failed to create stdout pipe: %v", err)
	}

	hostStderr, err := cmd.StderrPipe()
	if err != nil {
		fatal("failed to create stderr pipe: %v", err)
	}

	if err := cmd.Start(); err != nil {
		fatal("failed to start %s: %v", cmdName, err)
	}

	var wg sync.WaitGroup
	wg.Add(2) // Only wait for stdout + stderr relays, not stdin.

	// SPCS mode: if P67_RUN_MESSAGE_B64 is set, decode and inject it as
	// the first stdin message. In SPCS there is no stdin pipe from controld,
	// so the RunWorkflow message is passed as a base64-encoded env var.
	runMsgB64 := os.Getenv("P67_RUN_MESSAGE_B64")

	go func() {
		defer hostStdin.Close()
		if runMsgB64 != "" {
			decoded, err := base64.StdEncoding.DecodeString(runMsgB64)
			if err != nil {
				fmt.Fprintf(os.Stderr, "[p67-runner] failed to decode P67_RUN_MESSAGE_B64: %v\n", err)
				return
			}
			// Write decoded message + newline (NDJSON)
			hostStdin.Write(decoded)
			hostStdin.Write([]byte("\n"))
			// In SPCS mode there are no follow-up messages, so close stdin
			// to signal EOF to the host process.
			return
		}
		// Docker mode: relay our stdin → host stdin.
		io.Copy(hostStdin, os.Stdin)
	}()

	// SPCS mode: optionally tee host stdout to a results file so controld
	// can read structured messages from the stage after the job completes.
	resultsDir := os.Getenv("P67_RESULTS_DIR")
	var resultsFile *os.File
	if resultsDir != "" {
		if err := os.MkdirAll(resultsDir, 0o755); err != nil {
			fmt.Fprintf(os.Stderr, "[p67-runner] failed to create results dir %s: %v\n", resultsDir, err)
		} else {
			f, err := os.Create(filepath.Join(resultsDir, "messages.ndjson"))
			if err != nil {
				fmt.Fprintf(os.Stderr, "[p67-runner] failed to create results file: %v\n", err)
			} else {
				resultsFile = f
				defer resultsFile.Close()
			}
		}
	}

	// Relay host stdout → our stdout (IPC JSON messages).
	// When resultsFile is set, also write each line to the file.
	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(hostStdout)
		scanner.Buffer(make([]byte, 0, 1024*1024), 10*1024*1024) // 10MB max line
		for scanner.Scan() {
			line := scanner.Text()
			fmt.Println(line)
			if resultsFile != nil {
				resultsFile.WriteString(line + "\n")
			}
		}
	}()

	// Relay host stderr → our stderr with timestamps.
	go func() {
		defer wg.Done()
		reader := bufio.NewReader(hostStderr)
		for {
			line, err := reader.ReadString('\n')
			if len(line) > 0 {
				ts := time.Now().UTC().Format(time.RFC3339Nano)
				fmt.Fprintf(os.Stderr, "[%s] %s", ts, line)
			}
			if err != nil {
				if err != io.EOF {
					fmt.Fprintf(os.Stderr, "[p67-runner] stderr read error: %v\n", err)
				}
				break
			}
		}
	}()

	// Wait for IO goroutines to finish, then wait for the process to exit.
	wg.Wait()

	if err := cmd.Wait(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		fatal("workflow process error: %v", err)
	}
}

// detectLanguage inspects the workflow directory and returns the command name
// and arguments for the appropriate host process.
func detectLanguage(workflowDir string) (string, []string) {
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

// extractZip extracts a zip archive into destDir.
// Includes path traversal protection — entries that escape destDir are skipped.
func extractZip(zipPath, destDir string) error {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return fmt.Errorf("open zip: %w", err)
	}
	defer r.Close()

	cleanDest := filepath.Clean(destDir) + string(os.PathSeparator)

	for _, f := range r.File {
		target := filepath.Join(destDir, f.Name)

		// Path traversal protection: ensure the resolved path stays within destDir.
		if !strings.HasPrefix(filepath.Clean(target)+string(os.PathSeparator), cleanDest) &&
			filepath.Clean(target) != filepath.Clean(destDir) {
			fmt.Fprintf(os.Stderr, "[p67-runner] skipping unsafe zip entry: %s\n", f.Name)
			continue
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(target, 0o755)
			continue
		}

		// Ensure parent directory exists
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return fmt.Errorf("mkdir %s: %w", filepath.Dir(target), err)
		}

		outFile, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return fmt.Errorf("create %s: %w", target, err)
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return fmt.Errorf("open entry %s: %w", f.Name, err)
		}

		_, err = io.Copy(outFile, rc)
		rc.Close()
		outFile.Close()
		if err != nil {
			return fmt.Errorf("extract %s: %w", f.Name, err)
		}
	}
	return nil
}

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "[p67-runner] "+format+"\n", args...)
	os.Exit(1)
}
