// Command cli exposes api endpoints on the command line.
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"

	"dalnamics/services/cli/internal/commands"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	if err := commands.NewRootCmd().ExecuteContext(ctx); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
