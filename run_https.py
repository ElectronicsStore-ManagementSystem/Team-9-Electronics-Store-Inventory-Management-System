import os
import ssl

import uvicorn


def create_server() -> uvicorn.Server:
    certfile = os.getenv("EIMS_TLS_CERTFILE")
    keyfile = os.getenv("EIMS_TLS_KEYFILE")
    if not certfile or not keyfile:
        raise RuntimeError(
            "EIMS_TLS_CERTFILE and EIMS_TLS_KEYFILE must point to the TLS certificate and private key."
        )

    config = uvicorn.Config(
        "app.main:app",
        host=os.getenv("EIMS_HOST", "0.0.0.0"),
        port=int(os.getenv("EIMS_PORT", "8443")),
        ssl_certfile=certfile,
        ssl_keyfile=keyfile,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
        ssl_ciphers="TLSv1.2:TLSv1.3",
    )
    config.load()
    if config.ssl is None:
        raise RuntimeError("Uvicorn did not create a TLS context.")
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    return uvicorn.Server(config)


if __name__ == "__main__":
    create_server().run()
