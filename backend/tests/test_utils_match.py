from app.utils import url_in_feed


def test_exact_match():
    entries = {"evil.tk/login"}
    assert url_in_feed("https://evil.tk/login", entries) is True


def test_deeper_path_matches_reported_url():
    entries = {"github.com/user/repo/releases/download/x.zip"}
    assert url_in_feed("https://github.com/user/repo/releases/download/x.zip", entries) is True


def test_bare_host_not_tainted_by_deeper_report():
    entries = {"github.com/user/repo/releases/download/x.zip"}
    assert url_in_feed("https://github.com/", entries) is False


def test_unrelated_path_does_not_match():
    entries = {"github.com/user/repo/releases/download/x.zip"}
    assert url_in_feed("https://github.com/other/repo", entries) is False


def test_root_flag_taints_whole_domain():
    entries = {"evil.tk/"}
    assert url_in_feed("https://evil.tk/any/page", entries) is True
    assert url_in_feed("https://evil.tk/", entries) is True