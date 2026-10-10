// Package store is the api's Postgres data layer. sqlc generates one package
// per domain (e.g. store/auth) from queries/*.sql, and this package composes
// them into a single Querier, which is the only thing application code depends
// on and the only thing mocked.
package store

import (
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"dalnamics/services/api/internal/store/auth"
)

//go:generate go tool sqlc generate -f ../../sqlc.yaml
//go:generate go tool mockgen -destination mockstore/querier.go -package mockstore . Querier

// Querier is every query the api can run.
type Querier interface {
	auth.Querier
}

// Store implements Querier against a database connection or transaction.
type Store struct {
	*auth.Queries
}

var _ Querier = (*Store)(nil)

// New returns a Store backed by db (a *pgxpool.Pool, *pgx.Conn, or pgx.Tx).
func New(db auth.DBTX) *Store {
	return &Store{Queries: auth.New(db)}
}

// ErrNoRows is returned by :one queries that match nothing.
var ErrNoRows = pgx.ErrNoRows

// IsUniqueViolation reports whether err is a Postgres unique constraint violation.
func IsUniqueViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}
