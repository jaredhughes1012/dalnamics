package store

import (
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"dalnamics/services/devicemgr/internal/store/devices"
)

//go:generate go tool sqlc generate -f ../../sqlc.yaml
//go:generate go tool mockgen -destination mockstore/querier.go -package mockstore . Querier

// Querier is every query devicemgr can run. sqlc generates one package per
// domain (e.g. store/devices) from queries/*.sql, and Querier composes them; it
// is the only thing application code depends on and the only thing mocked.
type Querier interface {
	devices.Querier
}

// Store implements Querier against a database connection or transaction.
type Store struct {
	*devices.Queries
}

var _ Querier = (*Store)(nil)

// New returns a Store backed by db (a *pgxpool.Pool, *pgx.Conn, or pgx.Tx).
func New(db devices.DBTX) *Store {
	return &Store{Queries: devices.New(db)}
}

// ErrNoRows is returned by :one queries that match nothing.
var ErrNoRows = pgx.ErrNoRows

// IsUniqueViolation reports whether err is a Postgres unique constraint violation.
func IsUniqueViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}
