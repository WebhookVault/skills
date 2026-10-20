---
type: llm
---

The answer builds the signed string from the transmission id, transmission time, the stored webhook id and
the CRC-32 of the raw body, verifies the RSA SHA-256 signature with the certificate's public key, and only fetches
the certificate from PAYPAL-CERT-URL after checking it is https on a paypal.com host (explaining that otherwise
anyone could sign with their own certificate).
