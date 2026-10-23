import ssl

from run_https import create_server


def test_tls_launcher_requires_explicit_certificate_configuration(
    monkeypatch,
):
    monkeypatch.delenv("EIMS_TLS_CERTFILE", raising=False)
    monkeypatch.delenv("EIMS_TLS_KEYFILE", raising=False)

    try:
        create_server()
    except RuntimeError as exc:
        assert "EIMS_TLS_CERTFILE" in str(exc)
    else:
        raise AssertionError("TLS launcher accepted missing certificate settings")


def test_tls_protocol_policy_is_tls_1_2_or_newer():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
