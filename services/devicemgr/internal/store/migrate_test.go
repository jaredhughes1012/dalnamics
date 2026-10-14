package store

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMigrateURL(t *testing.T) {
	tests := map[string]struct {
		in, want string
	}{
		"postgres keeps params": {
			in:   "postgres://u:p@db:5432/dalnamics?sslmode=disable",
			want: "pgx5://u:p@db:5432/dalnamics?sslmode=disable&x-migrations-table=devicemgr_schema_migrations",
		},
		"postgresql without params": {
			in:   "postgresql://u:p@db/dalnamics",
			want: "pgx5://u:p@db/dalnamics?x-migrations-table=devicemgr_schema_migrations",
		},
	}
	for name, tt := range tests {
		t.Run(name, func(t *testing.T) {
			got, err := migrateURL(tt.in)
			require.NoError(t, err)
			assert.Equal(t, tt.want, got)
		})
	}
}
