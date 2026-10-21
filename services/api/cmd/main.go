// Command api serves the front-facing HTTP API.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"dalnamics/services/api/internal/auth"
	"dalnamics/services/api/internal/config"
	"dalnamics/services/api/internal/devices"
	"dalnamics/services/api/internal/server"
	"dalnamics/services/api/internal/store"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	cfg, err := config.Load(os.Getenv)
	if err != nil {
		logger.Error("invalid configuration", "err", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, cfg, logger); err != nil {
		logger.Error("api exited", "err", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, cfg config.Config, logger *slog.Logger) error {
	if err := store.Migrate(cfg.DatabaseURL); err != nil {
		return err
	}

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return fmt.Errorf("connect to database: %w", err)
	}
	defer pool.Close()

	q := store.New(pool)
	authSvc := auth.NewService(q, auth.Config{
		JWTSecret: cfg.JWTSecret,
		DevEmails: cfg.DevEmails,
	})
	devicesSvc := devices.NewService(q, devices.Config{})
	if cfg.Debug {
		if err := authSvc.SeedDevUsers(ctx); err != nil {
			return err
		}
		logger.Warn("DEBUG enabled: dev login is available", "dev_emails", cfg.DevEmails)
		if cfg.DevRegistrationCode != "" {
			if err := devicesSvc.SeedDevRegistrationCode(ctx, cfg.DevEmails[0], cfg.DevRegistrationCode); err != nil {
				return err
			}
			logger.Warn("DEBUG enabled: dev device registration code seeded", "email", cfg.DevEmails[0])
		}
	}

	handler, err := server.NewHandler(authSvc, devicesSvc, logger)
	if err != nil {
		return err
	}
	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}

	errc := make(chan error, 1)
	go func() {
		logger.Info("api listening", "addr", cfg.Addr)
		errc <- srv.ListenAndServe()
	}()

	select {
	case err := <-errc:
		return err
	case <-ctx.Done():
	}

	logger.Info("api shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return err
	}
	if err := <-errc; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}
