// Command devicemgr serves the internal device service's private HTTP API and
// handles device traffic as an MQTT client.
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

	"dalnamics/services/devicemgr/internal/config"
	"dalnamics/services/devicemgr/internal/devices"
	"dalnamics/services/devicemgr/internal/mqtt"
	"dalnamics/services/devicemgr/internal/server"
	"dalnamics/services/devicemgr/internal/store"
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
		logger.Error("devicemgr exited", "err", err)
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
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("ping database: %w", err)
	}

	devicesSvc := devices.NewService(store.New(pool), devices.Config{MQTTPassword: cfg.MQTTPassword})
	handler, err := server.NewHandler(cfg.Token, devicesSvc, logger)
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
		logger.Info("devicemgr listening", "addr", cfg.Addr)
		errc <- srv.ListenAndServe()
	}()

	// The broker calls back into the HTTP server to authenticate devicemgr, so
	// the server starts first; the MQTT client retries until both are up.
	mqttCtx, stopMQTT := context.WithCancel(context.Background())
	defer stopMQTT()
	broker, err := mqtt.Connect(mqttCtx, mqtt.Config{URL: cfg.MQTTURL, Password: cfg.MQTTPassword},
		mqtt.NewHandshake(devicesSvc, logger), logger)
	if err != nil {
		return err
	}

	select {
	case err := <-errc:
		return err
	case <-ctx.Done():
	}

	logger.Info("devicemgr shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := broker.Disconnect(shutdownCtx); err != nil {
		logger.Warn("mqtt disconnect", "err", err)
	}
	stopMQTT()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return err
	}
	if err := <-errc; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}
