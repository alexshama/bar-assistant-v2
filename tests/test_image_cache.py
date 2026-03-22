from services.image_cache import ImageCache


def test_cache_key_depends_on_full_prompt():
    cache = ImageCache(cache_dir="tests/.tmp/image-cache")

    key_one = cache._get_cache_key(
        "COCKTAIL_005_NEGRONI",
        "Professional cocktail photography of one classic Negroni in exactly one rocks glass.",
    )
    key_two = cache._get_cache_key(
        "COCKTAIL_005_NEGRONI",
        "Professional cocktail photography of one classic Negroni in exactly one rocks glass. No whipped cream.",
    )

    assert key_one != key_two


def test_b52_no_longer_uses_static_standard_key():
    cache = ImageCache(cache_dir="tests/.tmp/image-cache")

    key_value = cache._get_cache_key(
        "COCKTAIL_045_B-52",
        "Professional cocktail photography of one B-52 layered shot with exactly three distinct layers.",
    )

    assert not key_value.endswith("_standard")
