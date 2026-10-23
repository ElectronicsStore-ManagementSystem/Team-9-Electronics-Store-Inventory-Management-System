# Authentication policy

All inventory, dashboard, availability, audit-log, and current-user endpoints
require a valid bearer token. The login endpoint is the only API endpoint that
creates a token, and the health endpoint remains public for service monitoring.

Clients must first authenticate:

```http
POST /api/auth/login
Content-Type: application/json

{"username":"staff","password":"Staff@12345"}
```

Use the returned token on protected requests:

```http
Authorization: Bearer <access-token>
```

Requests without credentials, with malformed credentials, or with an invalid,
expired, inactive-user, or missing-user token receive `401 Unauthorized` and a
`WWW-Authenticate: Bearer` response header. A valid token without the required
role receives `403 Forbidden`.
