// Package commands defines the cli's cobra command tree.
package commands

import (
	"os"

	"github.com/spf13/cobra"

	"dalnamics/services/cli/internal/client"
	"dalnamics/services/cli/internal/credentials"
)

const (
	defaultAPIURL    = "http://localhost:8080"
	defaultStudioURL = "http://localhost:5173"
)

// env holds what commands need from the root command's flags.
type env struct {
	apiURL    string
	studioURL string
}

// client returns an api client that authenticates with the stored credentials.
func (e *env) client() (*client.Client, error) {
	creds, err := credentials.New()
	if err != nil {
		return nil, err
	}
	return client.New(e.apiURL, creds)
}

// NewRootCmd builds the root command and all of its subcommands.
func NewRootCmd() *cobra.Command {
	e := &env{}

	root := &cobra.Command{
		Use:           "cli",
		Short:         "Command line interface to the dalnamics api",
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	flags := root.PersistentFlags()
	flags.StringVar(&e.apiURL, "api-url", envOr("DALNAMICS_API_URL", defaultAPIURL), "base URL of the api (env DALNAMICS_API_URL)")
	flags.StringVar(&e.studioURL, "studio-url", envOr("DALNAMICS_STUDIO_URL", defaultStudioURL), "base URL of studio, used for browser login (env DALNAMICS_STUDIO_URL)")

	root.AddCommand(
		newHealthCmd(e),
		newAuthCmd(e),
		newDevicesCmd(e),
	)

	return root
}

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}
