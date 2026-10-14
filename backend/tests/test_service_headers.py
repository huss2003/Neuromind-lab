from app import http


def test_legacy_jwt_key_goes_in_both_headers():
    assert http.service_headers("eyJhbGciOi.x.y") == {"apikey": "eyJhbGciOi.x.y", "Authorization": "Bearer eyJhbGciOi.x.y"}


def test_new_secret_key_is_sent_in_apikey_only():
    assert http.service_headers("sb_secret_abc") == {"apikey": "sb_secret_abc"}
