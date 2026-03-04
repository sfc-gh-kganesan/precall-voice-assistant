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
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
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

	// Relay our stdin → host stdin.
	// This goroutine is NOT part of the WaitGroup because controld keeps stdin
	// open for follow-up messages (OAuth, interrupts).  When the host process
	// exits, hostStdin.Close() is a no-op and the goroutine will exit once the
	// container shuts down.
	go func() {
		defer hostStdin.Close()
		io.Copy(hostStdin, os.Stdin)
	}()

	// Relay host stdout → our stdout (IPC JSON messages).
	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(hostStdout)
		scanner.Buffer(make([]byte, 0, 1024*1024), 10*1024*1024) // 10MB max line
		for scanner.Scan() {
			fmt.Println(scanner.Text())
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

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "[p67-runner] "+format+"\n", args...)
	os.Exit(1)
}
