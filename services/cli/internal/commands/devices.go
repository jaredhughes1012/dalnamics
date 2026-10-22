package commands

import (
	"encoding/json"
	"errors"
	"fmt"
	"text/tabwriter"
	"time"

	"github.com/google/uuid"
	"github.com/spf13/cobra"

	"dalnamics/services/cli/internal/client"
)

func newDevicesCmd(e *env) *cobra.Command {
	cmd := &cobra.Command{
		Use:   "devices",
		Short: "Register, list, view, and rename your devices",
	}
	cmd.AddCommand(newDevicesRegisterCmd(e), newDevicesListCmd(e), newDevicesGetCmd(e), newDevicesRenameCmd(e))
	return cmd
}

func newDevicesRegisterCmd(e *env) *cobra.Command {
	var asJSON bool

	cmd := &cobra.Command{
		Use:   "register",
		Short: "Get a one-time code that registers a device to you",
		Long: `Get a one-time code that registers a device to you.

Give the code to the device (for harwood0, set HARWOOD0_REGISTRATION_CODE). The
code works once and expires after 10 minutes. Run ` + "`cli devices list`" + ` to see
the device once it has registered.`,
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			c, err := e.client()
			if err != nil {
				return err
			}
			rc, err := c.CreateDeviceRegistrationCode(cmd.Context())
			if err != nil {
				return notLoggedIn(err)
			}
			if asJSON {
				return json.NewEncoder(cmd.OutOrStdout()).Encode(rc)
			}
			minutes := int(time.Until(rc.ExpiresAt).Round(time.Minute) / time.Minute)
			_, err = fmt.Fprintf(cmd.OutOrStdout(), "Enter code %s on the device. It expires at %s (%d min).\n",
				rc.Code, rc.ExpiresAt.Local().Format("15:04"), minutes)
			return err
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print the raw JSON response")

	return cmd
}

func newDevicesListCmd(e *env) *cobra.Command {
	var asJSON bool

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List your devices, newest first",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			c, err := e.client()
			if err != nil {
				return err
			}
			devices, err := c.ListDevices(cmd.Context())
			if err != nil {
				return notLoggedIn(err)
			}
			out := cmd.OutOrStdout()
			if asJSON {
				return json.NewEncoder(out).Encode(devices)
			}
			if len(devices) == 0 {
				_, err = fmt.Fprintln(out, "No devices registered. Run `cli devices register` to add one.")
				return err
			}
			tw := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
			fmt.Fprintln(tw, "ID\tNAME\tTYPE\tSTATUS\tREGISTERED")
			for _, d := range devices {
				fmt.Fprintf(tw, "%s\t%s\t%s\t%s\t%s\n", d.Id, d.Name, d.Type, onlineStatus(d.Online), d.CreatedAt.Local().Format(time.DateTime))
			}
			return tw.Flush()
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print the raw JSON response")

	return cmd
}

func newDevicesGetCmd(e *env) *cobra.Command {
	var asJSON bool

	cmd := &cobra.Command{
		Use:   "get <id>",
		Short: "Show one of your devices",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			id, err := uuid.Parse(args[0])
			if err != nil {
				return fmt.Errorf("invalid device id %q: must be a UUID", args[0])
			}
			c, err := e.client()
			if err != nil {
				return err
			}
			d, err := c.GetDevice(cmd.Context(), id)
			if client.IsNotFound(err) {
				return fmt.Errorf("device %s not found", id)
			}
			if err != nil {
				return notLoggedIn(err)
			}
			out := cmd.OutOrStdout()
			if asJSON {
				return json.NewEncoder(out).Encode(d)
			}
			lastSeen := "never"
			if d.LastSeenAt != nil {
				lastSeen = d.LastSeenAt.Local().Format(time.DateTime)
			}
			tw := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
			fmt.Fprintf(tw, "ID\t%s\n", d.Id)
			fmt.Fprintf(tw, "NAME\t%s\n", d.Name)
			fmt.Fprintf(tw, "TYPE\t%s\n", d.Type)
			fmt.Fprintf(tw, "STATUS\t%s\n", onlineStatus(d.Online))
			fmt.Fprintf(tw, "LAST SEEN\t%s\n", lastSeen)
			fmt.Fprintf(tw, "REGISTERED\t%s\n", d.CreatedAt.Local().Format(time.DateTime))
			return tw.Flush()
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print the raw JSON response")

	return cmd
}

func newDevicesRenameCmd(e *env) *cobra.Command {
	var asJSON bool

	cmd := &cobra.Command{
		Use:   "rename <id> <name>",
		Short: "Rename one of your devices",
		Long: `Rename one of your devices.

Quote a name with spaces. The name is trimmed and must be 1-100 characters. The
new name shows everywhere the device is listed.`,
		Example: `  cli devices rename 6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11 "Bench rover"`,
		Args:    cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			id, err := uuid.Parse(args[0])
			if err != nil {
				return fmt.Errorf("invalid device id %q: must be a UUID", args[0])
			}
			c, err := e.client()
			if err != nil {
				return err
			}
			d, err := c.RenameDevice(cmd.Context(), id, args[1])
			if client.IsNotFound(err) {
				return fmt.Errorf("device %s not found", id)
			}
			var apiErr *client.APIError
			if errors.As(err, &apiErr) && apiErr.Code == "invalid_request" {
				return errors.New(apiErr.Message)
			}
			if err != nil {
				return notLoggedIn(err)
			}
			out := cmd.OutOrStdout()
			if asJSON {
				return json.NewEncoder(out).Encode(d)
			}
			_, err = fmt.Fprintf(out, "Renamed device %s to %q.\n", d.Id, d.Name)
			return err
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print the raw JSON response")

	return cmd
}

func onlineStatus(online bool) string {
	if online {
		return "online"
	}
	return "offline"
}
