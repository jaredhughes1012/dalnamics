package auth

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"net"
	"net/url"
)

// verifyPKCE reports whether verifier hashes to challenge using the S256 method.
func verifyPKCE(verifier, challenge string) bool {
	sum := sha256.Sum256([]byte(verifier))
	got := base64.RawURLEncoding.EncodeToString(sum[:])
	return subtle.ConstantTimeCompare([]byte(got), []byte(challenge)) == 1
}

// validChallenge reports whether challenge looks like a base64url SHA-256.
func validChallenge(challenge string) bool {
	b, err := base64.RawURLEncoding.DecodeString(challenge)
	return err == nil && len(b) == sha256.Size
}

// isLoopbackRedirect reports whether uri is an http URL on a loopback
// address with an explicit port, which is the only place a cli listens.
func isLoopbackRedirect(uri string) bool {
	u, err := url.Parse(uri)
	if err != nil || u.Scheme != "http" || u.Port() == "" || u.User != nil {
		return false
	}
	host := u.Hostname()
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}
