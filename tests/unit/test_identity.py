from nfl_analytics.presentation.identity import avatar, image_url


def test_images_require_safe_https_and_escape_labels():
    assert image_url("javascript:alert(1)") is None
    assert image_url("https://[") is None
    assert image_url(None) is None
    assert image_url("https://example.org/photo.png") == "https://example.org/photo.png"
    assert '<script>' not in avatar(None, '<script>')


def test_missing_photo_keeps_player_initials():
    result = avatar(None, "Josh Allen", player=True)
    assert "JA" in result
    assert "<img" not in result
