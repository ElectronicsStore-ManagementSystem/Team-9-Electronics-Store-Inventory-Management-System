# HTTPS and TLS policy

EIMS enforces HTTPS by default with `EIMS_ENFORCE_HTTPS=true`. Direct HTTP
requests receive an HTTPS redirect before protected routes are processed.
Local development and automated tests may explicitly set
`EIMS_ENFORCE_HTTPS=false`.

Production should use [run_https.py](../run_https.py) with a certificate and
private key supplied through `EIMS_TLS_CERTFILE` and `EIMS_TLS_KEYFILE`.
The launcher:

- requires both certificate paths;
- sets the SSL context minimum version to TLS 1.2; and
- limits configured ciphers to TLS 1.2 and TLS 1.3.

When TLS is terminated by a reverse proxy or load balancer, configure that
edge service to:

1. redirect all HTTP requests to HTTPS;
2. disable TLS versions below 1.2;
3. use a trusted certificate; and
4. forward only HTTPS traffic to EIMS.

Do not set `EIMS_ENFORCE_HTTPS=false` in a production deployment.
