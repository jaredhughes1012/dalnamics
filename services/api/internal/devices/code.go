package devices

import (
	"crypto/rand"
	"crypto/sha256"
	"strings"
)

// codeAlphabet has 32 characters, leaving out 0/O and 1/I, which are easy to
// confuse when a code is read off a screen and typed into a device.
const codeAlphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

const codeLen = 6

// generateCode returns a random registration code. The alphabet has 32
// characters, so masking each random byte to 5 bits picks uniformly.
func generateCode() string {
	b := make([]byte, codeLen)
	_, _ = rand.Read(b) // never returns an error
	for i := range b {
		b[i] = codeAlphabet[b[i]&31]
	}
	return string(b)
}

// hashCode returns the stored form of a code: SHA-256 of the code trimmed and
// uppercased, so codes compare case-insensitively. devicemgr hashes codes the
// same way when a device redeems one.
func hashCode(code string) []byte {
	sum := sha256.Sum256([]byte(strings.ToUpper(strings.TrimSpace(code))))
	return sum[:]
}
