// p67-runner is a lightweight process supervisor for p67 workflow execution.
//
// It fork-execs the Python host process (host.py), feeds it a RunWorkflow
// message over stdin, and captures stdout (IPC JSON) and stderr (workflow
// logs) separately. This gives us a single hook point for log capture,
// timeouts, and resource limits in future iterations.
//
// Usage:
//
//	p67-runner <workflow-dir>
//
// Environment:
//
//	P67_RUN_CONFIG  – JSON string with the RunWorkflow config payload
//	P67_HOST_SCRIPT – path to host.py (default: /app/host.py)
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
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

	// Build the RunWorkflow message.
	configJSON := os.Getenv("P67_RUN_CONFIG")
	if configJSON == "" {
		configJSON = `{"snowflakeConfig":{},"parameters":{}}`
	}

	var config json.RawMessage
	if err := json.Unmarshal([]byte(configJSON), &config); err != nil {
		fatal("invalid P67_RUN_CONFIG: %v", err)
	}

	runMsg := map[string]any{
		"type":   "RunWorkflow",
		"dir":    workflowDir,
		"config": config,
	}

	runMsgBytes, err := json.Marshal(runMsg)
	if err != nil {
		fatal("failed to marshal RunWorkflow message: %v", err)
	}

	// Resolve host script path.
	hostScript := os.Getenv("P67_HOST_SCRIPT")
	if hostScript == "" {
		hostScript = "/app/host.py"
	}

	if _, err := os.Stat(hostScript); err != nil {
		fatal("host script not found: %s", hostScript)
	}

	// Start the Python host process.
	cmd := exec.Command("python3", hostScript)
	cmd.Dir = workflowDir

	stdin, err := cmd.StdinPipe()
	if err != nil {
		fatal("failed to create stdin pipe: %v", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		fatal("failed to create stdout pipe: %v", err)
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		fatal("failed to create stderr pipe: %v", err)
	}

	if err := cmd.Start(); err != nil {
		fatal("failed to start python3: %v", err)
	}

	// Send the RunWorkflow message then close stdin to signal no more input.
	// (For future interrupt support, we'd keep stdin open.)
	stdin.Write(runMsgBytes)
	stdin.Write([]byte("\n"))
	stdin.Close()

	// Capture stdout (IPC messages) and stderr (workflow logs) concurrently.
	var wg sync.WaitGroup
	wg.Add(2)

	// Stdout: IPC JSON messages from the host process.
	// Forward them to our own stdout so the orchestrator can read them.
	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(stdout)
		scanner.Buffer(make([]byte, 0, 1024*1024), 10*1024*1024) // 10MB max line
		for scanner.Scan() {
			fmt.Println(scanner.Text())
		}
	}()

	// Stderr: workflow print() output and host diagnostics.
	// Prefix each line with a timestamp for structured logging.
	go func() {
		defer wg.Done()
		reader := bufio.NewReader(stderr)
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

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "[p67-runner] "+format+"\n", args...)
	os.Exit(1)
}
