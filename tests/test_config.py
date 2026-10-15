from app.config import normalize_mongodb_uri


def test_mongodb_uri_escapes_special_password_characters():
    uri = "mongodb+srv://bluecap:p@ss:word#1@cluster.rhzotfg.mongodb.net/"

    normalized = normalize_mongodb_uri(uri)

    assert normalized == (
        "mongodb+srv://bluecap:p%40ss%3Aword%231@"
        "cluster.rhzotfg.mongodb.net/"
    )

