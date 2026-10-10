package commands

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"

	"dalnamics/services/cli/internal/client"
)

func newHealthCmd(newClient func() *client.Client) *cobra.Command {
	var asJSON bool

	cmd := &cobra.Command{
		Use:   "health",
		Short: "Ping the api health check",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			res, err := newClient().Health(cmd.Context())
			if err != nil {
				return fmt.Errorf("api unhealthy: %w", err)
			}
			if asJSON {
				return json.NewEncoder(cmd.OutOrStdout()).Encode(res)
			}
			_, err = fmt.Fprintf(cmd.OutOrStdout(), "%s: %s\n", res.Service, res.Status)
			return err
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print the raw JSON response")

	return cmd
}
