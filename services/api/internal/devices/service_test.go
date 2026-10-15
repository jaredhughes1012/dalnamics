package devices

import (
	"context"
	"crypto/sha256"
	"errors"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/services/api/internal/store"
	storedevices "dalnamics/services/api/internal/store/devices"
	"dalnamics/services/api/internal/store/mockstore"
)

var testNow = time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)

func newMockedService(t *testing.T) (*Service, *mockstore.MockQuerier) {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	return NewService(q, Config{Now: func() time.Time { return testNow }}), q
}

// expectTx runs each InTx callback against q itself.
func expectTx(q *mockstore.MockQuerier, times int) {
	q.EXPECT().InTx(gomock.Any(), gomock.Any()).Times(times).
		DoAndReturn(func(_ context.Context, fn func(store.Querier) error) error { return fn(q) })
}

func TestGenerateCode(t *testing.T) {
	seen := map[string]bool{}
	for range 200 {
		code := generateCode()
		require.Len(t, code, codeLen)
		for _, c := range code {
			assert.Contains(t, codeAlphabet, string(c))
		}
		seen[code] = true
	}
	assert.Greater(t, len(seen), 190, "codes should rarely repeat")
}

func TestHashCodeNormalizes(t *testing.T) {
	want := sha256.Sum256([]byte("AB3D7K"))
	assert.Equal(t, want[:], hashCode("AB3D7K"))
	assert.Equal(t, want[:], hashCode("  ab3d7k\n"))
}

func TestIssueRegistrationCode(t *testing.T) {
	s, q := newMockedService(t)
	userID := uuid.New()

	expectTx(q, 1)
	var stored storedevices.CreateDeviceRegistrationCodeParams
	gomock.InOrder(
		q.EXPECT().DeleteExpiredDeviceRegistrationCodes(gomock.Any()).Return(nil),
		q.EXPECT().CreateDeviceRegistrationCode(gomock.Any(), gomock.Any()).
			DoAndReturn(func(_ context.Context, p storedevices.CreateDeviceRegistrationCodeParams) error {
				stored = p
				return nil
			}),
	)

	rc, err := s.IssueRegistrationCode(context.Background(), userID)
	require.NoError(t, err)
	assert.Len(t, rc.Code, codeLen)
	assert.Equal(t, testNow.Add(10*time.Minute), rc.ExpiresAt)

	sum := sha256.Sum256([]byte(rc.Code))
	assert.Equal(t, sum[:], stored.CodeHash, "only the hash of the code is stored")
	assert.Equal(t, userID, stored.UserID)
	assert.Equal(t, rc.ExpiresAt, stored.ExpiresAt)
}

func TestIssueRegistrationCodeRetriesCollisions(t *testing.T) {
	s, q := newMockedService(t)
	collision := &pgconn.PgError{Code: "23505"}

	expectTx(q, 2)
	q.EXPECT().DeleteExpiredDeviceRegistrationCodes(gomock.Any()).Return(nil).Times(2)
	var hashes [][]byte
	q.EXPECT().CreateDeviceRegistrationCode(gomock.Any(), gomock.Any()).Times(2).
		DoAndReturn(func(_ context.Context, p storedevices.CreateDeviceRegistrationCodeParams) error {
			hashes = append(hashes, p.CodeHash)
			if len(hashes) == 1 {
				return collision
			}
			return nil
		})

	_, err := s.IssueRegistrationCode(context.Background(), uuid.New())
	require.NoError(t, err)
	assert.NotEqual(t, hashes[0], hashes[1], "a retry uses a new code")
}

func TestIssueRegistrationCodeGivesUpAfterThreeCollisions(t *testing.T) {
	s, q := newMockedService(t)

	expectTx(q, 3)
	q.EXPECT().DeleteExpiredDeviceRegistrationCodes(gomock.Any()).Return(nil).Times(3)
	q.EXPECT().CreateDeviceRegistrationCode(gomock.Any(), gomock.Any()).Return(&pgconn.PgError{Code: "23505"}).Times(3)

	_, err := s.IssueRegistrationCode(context.Background(), uuid.New())
	require.Error(t, err)
	assert.ErrorContains(t, err, "collided")
}

func TestIssueRegistrationCodeFailsWhenCleanupFails(t *testing.T) {
	s, q := newMockedService(t)
	boom := errors.New("boom")

	expectTx(q, 1)
	q.EXPECT().DeleteExpiredDeviceRegistrationCodes(gomock.Any()).Return(boom)

	_, err := s.IssueRegistrationCode(context.Background(), uuid.New())
	assert.ErrorIs(t, err, boom)
}

func TestList(t *testing.T) {
	s, q := newMockedService(t)
	userID := uuid.New()
	want := []Device{{ID: uuid.New(), Type: "harwood0", Name: "bench", CreatedAt: testNow}}
	q.EXPECT().ListDevicesByUser(gomock.Any(), userID).Return(want, nil)

	got, err := s.List(context.Background(), userID)
	require.NoError(t, err)
	assert.Equal(t, want, got)
}
