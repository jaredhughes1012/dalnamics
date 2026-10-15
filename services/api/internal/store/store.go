// Package store is the api's Postgres data layer. sqlc generates one package
// per domain (e.g. store/auth) from queries/*.sql, and this package composes
// them into a single Querier, which is the only thing application code depends
// on and the only thing mocked.
package store

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"dalnamics/services/api/internal/store/auth"
	"dalnamics/services/api/internal/store/devices"
)

//go:generate go tool sqlc generate -f ../../sqlc.yaml
//go:generate go tool mockgen -destination mockstore/querier.go -package mockstore . Querier

// Querier is every query the api can run.
type Querier interface {
	auth.Querier
	devices.Querier

	// InTx runs fn against a Querier bound to one transaction, committing if
	// fn returns nil and rolling back otherwise.
	InTx(ctx context.Context, fn func(Querier) error) error
}

// DB is a connection that can start transactions: a *pgxpool.Pool, *pgx.Conn,
// or pgx.Tx (which nests as a savepoint).
type DB interface {
	auth.DBTX
	Begin(ctx context.Context) (pgx.Tx, error)
}

// Each domain's generated type is named Queries, so they are embedded through
// aliases to give the fields distinct names.
type (
	authQueries    = auth.Queries
	devicesQueries = devices.Queries
)

// Store implements Querier against a database connection or transaction.
type Store struct {
	*authQueries
	*devicesQueries

	db DB
}

var _ Querier = (*Store)(nil)

// New returns a Store backed by db.
func New(db DB) *Store {
	return &Store{authQueries: auth.New(db), devicesQueries: devices.New(db), db: db}
}

// InTx implements Querier.
func (s *Store) InTx(ctx context.Context, fn func(Querier) error) error {
	tx, err := s.db.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	if err := fn(New(tx)); err != nil {
		return errors.Join(err, tx.Rollback(ctx))
	}
	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("commit transaction: %w", err)
	}
	return nil
}

// ErrNoRows is returned by :one queries that match nothing.
var ErrNoRows = pgx.ErrNoRows

// IsUniqueViolation reports whether err is a Postgres unique constraint violation.
func IsUniqueViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}
