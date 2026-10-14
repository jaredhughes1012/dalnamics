// Package store owns devicemgr's Postgres schema, devicemgr.
package store

import (
	"embed"
	"errors"
	"fmt"
	"net/url"
	"strings"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5" // registers the pgx5:// driver
	"github.com/golang-migrate/migrate/v4/source/iofs"
)

// migrationsTable tracks applied migrations. golang-migrate creates it before
// running any migration, so it lives in public (beside the api's
// schema_migrations) rather than in the devicemgr schema a migration creates.
const migrationsTable = "devicemgr_schema_migrations"

//go:embed migrations/*.sql
var migrations embed.FS

// Migrate applies all pending up migrations to the database at databaseURL.
func Migrate(databaseURL string) error {
	src, err := iofs.New(migrations, "migrations")
	if err != nil {
		return fmt.Errorf("load migrations: %w", err)
	}
	u, err := migrateURL(databaseURL)
	if err != nil {
		return err
	}
	m, err := migrate.NewWithSourceInstance("iofs", src, u)
	if err != nil {
		return fmt.Errorf("init migrations: %w", err)
	}
	defer m.Close()

	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("apply migrations: %w", err)
	}
	return nil
}

// migrateURL swaps a postgres:// URL to the pgx5:// scheme golang-migrate
// expects and points it at devicemgr's migrations table.
func migrateURL(databaseURL string) (string, error) {
	for _, prefix := range []string{"postgres://", "postgresql://"} {
		if rest, ok := strings.CutPrefix(databaseURL, prefix); ok {
			databaseURL = "pgx5://" + rest
			break
		}
	}
	u, err := url.Parse(databaseURL)
	if err != nil {
		return "", fmt.Errorf("parse DATABASE_URL: %w", err)
	}
	q := u.Query()
	q.Set("x-migrations-table", migrationsTable)
	u.RawQuery = q.Encode()
	return u.String(), nil
}
