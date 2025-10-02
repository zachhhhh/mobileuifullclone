# Security Hardening Checklist

## Backend
- [ ] Configure environment secrets (`backend/.env`) and rotate keys regularly
- [ ] Enforce HTTPS (reverse proxy / TLS termination)
- [ ] Restrict CORS origins to trusted hosts
- [ ] Implement authentication & authorization (JWT/OAuth/session)
- [ ] Add rate limiting / bot protection
- [ ] Monitor logs for anomalies and integrate with SIEM

## iOS Client
- [ ] Implement certificate pinning (URLSession delegate)
- [ ] Secure storage (Keychain) for tokens/secrets
- [ ] Obfuscate sensitive strings and analytics keys
- [ ] Verify ATS (App Transport Security) configuration

## Android Client
- [ ] Enable Network Security Config with pinning
- [ ] Store credentials in EncryptedSharedPreferences / Keystore
- [ ] Protect against tapjacking/debugging (FLAG_SECURE, debuggable=false)

## Analytics & Privacy
- [ ] Ensure consent flows match source app requirements
- [ ] Audit analytics events and scrub PII
- [ ] Document data retention and deletion policies

Update this checklist as you progress and reference it during release reviews.
