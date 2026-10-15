package commands

import (
	"errors"
	"fmt"

	"github.com/pkg/browser"
	"github.com/spf13/cobra"

	"dalnamics/services/cli/internal/client"
	"dalnamics/services/cli/internal/client/apigen"
	"dalnamics/services/cli/internal/login"
)

func newAuthCmd(e *env) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "auth",
		Short: "Log in to and out of the api",
	}
	cmd.AddCommand(newLoginCmd(e), newLogoutCmd(e), newStatusCmd(e))
	return cmd
}

func newLoginCmd(e *env) *cobra.Command {
	var devEmail string
	var noBrowser bool

	cmd := &cobra.Command{
		Use:   "login",
		Short: "Log in through studio in your browser",
		Long: `Log in through studio in your browser.

The cli opens studio, where you log in (or reuse an existing studio session)
and approve the cli. Credentials are stored in the OS keychain, or in an
owner-only file when no keychain is available.

With --dev, log in directly as a dev user. This only works when the api runs
with DEBUG=true and the email is listed in DEV_EMAILS.`,
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			c, err := e.client()
			if err != nil {
				return err
			}

			var user apigen.User
			if devEmail != "" {
				user, err = c.DevLogin(cmd.Context(), devEmail)
			} else {
				opts := login.Options{StudioURL: e.studioURL, Out: cmd.ErrOrStderr()}
				if !noBrowser {
					opts.OpenBrowser = browser.OpenURL
				}
				user, err = login.Browser(cmd.Context(), c, opts)
			}
			if err != nil {
				return fmt.Errorf("login failed: %w", err)
			}

			_, err = fmt.Fprintf(cmd.OutOrStdout(), "Logged in to %s as %s <%s>\n", c.BaseURL, user.Name, user.Email)
			return err
		},
	}
	cmd.Flags().StringVar(&devEmail, "dev", "", "log in as this dev user without a browser")
	cmd.Flags().BoolVar(&noBrowser, "no-browser", false, "print the login URL instead of opening a browser")

	return cmd
}

func newLogoutCmd(e *env) *cobra.Command {
	return &cobra.Command{
		Use:   "logout",
		Short: "Revoke the cli's session and delete stored credentials",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			c, err := e.client()
			if err != nil {
				return err
			}
			if err := c.Logout(cmd.Context()); err != nil {
				return err
			}
			_, err = fmt.Fprintf(cmd.OutOrStdout(), "Logged out of %s\n", c.BaseURL)
			return err
		},
	}
}

func newStatusCmd(e *env) *cobra.Command {
	return &cobra.Command{
		Use:   "status",
		Short: "Show the logged-in user",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			c, err := e.client()
			if err != nil {
				return err
			}
			user, err := c.Me(cmd.Context())
			if err != nil {
				return notLoggedIn(err)
			}
			_, err = fmt.Fprintf(cmd.OutOrStdout(), "Logged in to %s as %s <%s>\n", c.BaseURL, user.Name, user.Email)
			return err
		},
	}
}

// notLoggedIn replaces a 401 with the hint to log in.
func notLoggedIn(err error) error {
	if client.IsUnauthorized(err) {
		return errors.New("not logged in; run `cli auth login`")
	}
	return err
}
