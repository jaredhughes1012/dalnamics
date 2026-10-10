// Package commands defines the cli's cobra command tree.
package commands

import (
	"os"

	"github.com/spf13/cobra"

	"dalnamics/services/cli/internal/client"
)

const defaultAPIURL = "http://localhost:8080"

// NewRootCmd builds the root command and all of its subcommands.
func NewRootCmd() *cobra.Command {
	var apiURL string

	root := &cobra.Command{
		Use:           "cli",
		Short:         "Command line interface to the dalnamics api",
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	root.PersistentFlags().StringVar(&apiURL, "api-url", envOr("DALNAMICS_API_URL", defaultAPIURL), "base URL of the api (env DALNAMICS_API_URL)")

	newClient := func() *client.Client { return client.New(apiURL) }
	root.AddCommand(newHealthCmd(newClient))

	return root
}

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}
