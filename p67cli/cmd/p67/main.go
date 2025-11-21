package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/spf13/cobra"
)

// Version information (set at build time)
var (
	version = "0.1.0"
	commit  = "dev"
)

// Global flags
var (
	verbose bool
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("205")).
			MarginBottom(1)

	itemStyle = lipgloss.NewStyle().
			PaddingLeft(2)

	selectedStyle = lipgloss.NewStyle().
			PaddingLeft(2).
			Foreground(lipgloss.Color("170")).
			Bold(true)

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("241")).
			MarginTop(1)
)

// View state
type viewState int

const (
	menuView viewState = iota
	generateAgentView
)

// Model represents the TUI state
type model struct {
	choices   []string
	cursor    int
	view      viewState
	agentName string
	quitting  bool
	message   string
}

func initialModel() model {
	return model{
		choices: []string{"Generate a new agent", "Exit"},
		view:    menuView,
	}
}

// Init implements tea.Model
func (m model) Init() tea.Cmd {
	return nil
}

// Update implements tea.Model
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch m.view {
		case menuView:
			return m.updateMenu(msg)
		case generateAgentView:
			return m.updateGenerateAgent(msg)
		}
	}
	return m, nil
}

func (m model) updateMenu(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c", "q":
		m.quitting = true
		return m, tea.Quit

	case "up", "k":
		if m.cursor > 0 {
			m.cursor--
		}

	case "down", "j":
		if m.cursor < len(m.choices)-1 {
			m.cursor++
		}

	case "enter":
		switch m.cursor {
		case 0: // Generate a new agent
			m.view = generateAgentView
			m.agentName = ""
		case 1: // Exit
			m.quitting = true
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m model) updateGenerateAgent(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c":
		m.quitting = true
		return m, tea.Quit

	case "esc":
		m.view = menuView
		m.agentName = ""
		m.message = ""

	case "enter":
		if len(m.agentName) > 0 {
			m.message = fmt.Sprintf("Agent '%s' created successfully!", m.agentName)
			m.agentName = ""
		}

	case "backspace":
		if len(m.agentName) > 0 {
			m.agentName = m.agentName[:len(m.agentName)-1]
		}

	default:
		// Add character to agent name (single printable chars only)
		if len(msg.String()) == 1 {
			m.agentName += msg.String()
		}
	}
	return m, nil
}

// View implements tea.Model
func (m model) View() string {
	if m.quitting {
		return "Goodbye!\n"
	}

	switch m.view {
	case generateAgentView:
		return m.viewGenerateAgent()
	default:
		return m.viewMenu()
	}
}

func (m model) viewMenu() string {
	s := titleStyle.Render("p67 - Main Menu") + "\n\n"

	for i, choice := range m.choices {
		cursor := " "
		if m.cursor == i {
			cursor = ">"
		}

		line := fmt.Sprintf("%s %s", cursor, choice)
		if m.cursor == i {
			s += selectedStyle.Render(line) + "\n"
		} else {
			s += itemStyle.Render(line) + "\n"
		}
	}

	s += helpStyle.Render("\n↑/k up • ↓/j down • enter select • q quit")

	return s
}

func (m model) viewGenerateAgent() string {
	s := titleStyle.Render("Generate New Agent") + "\n\n"

	s += "Enter agent name: " + m.agentName + "█\n"

	if m.message != "" {
		successStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
		s += "\n" + successStyle.Render(m.message) + "\n"
	}

	s += helpStyle.Render("\nenter confirm • esc back • ctrl+c quit")

	return s
}

func runTUI() error {
	p := tea.NewProgram(initialModel())
	_, err := p.Run()
	return err
}

func main() {
	rootCmd := &cobra.Command{
		Use:   "p67",
		Short: "Agent workflow builder",
		Long:  `p67 is a command-line application used for building agentic workflows.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			if verbose {
				fmt.Println("Verbose mode enabled")
				fmt.Printf("Version: %s (commit: %s)\n", version, commit)
			}
			return runTUI()
		},
	}

	// Global flags
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "Enable verbose output")

	// Version command
	versionCmd := &cobra.Command{
		Use:   "version",
		Short: "Print version information",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("p67 version %s (commit: %s)\n", version, commit)
		},
	}

	rootCmd.AddCommand(versionCmd)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
