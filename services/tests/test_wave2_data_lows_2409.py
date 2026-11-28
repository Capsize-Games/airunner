"""Wave-2 data LOWs omnibus regressions (#2409, data slice).

Covers the two bullets whose fixes had no success-path lock:
curated geolocation ``display_name`` and the VACUUM INTO pause
disclosure. The other three bullets (bootstrap insert-only, ZIM
batching, EPUB page_ fallback) already have regression coverage in
``test_wave2_data_boundaries.py`` and ``test_wave2_art_data_fixes.py``.
"""

from __future__ import annotations

import asyncio


def test_geolocate_returns_curated_display_name(monkeypatch) -> None:
    """A resolved ZIP returns ``ZCTA <zip>``, never row-dict internals."""
    pd = __import__("pandas")
    from airunner_services.api.routes import geolocation

    frame = pd.DataFrame(
        [
            {
                "GEOID": "90210",
                "INTPTLAT": "34.0901",
                "INTPTLONG": "-118.4065",
            }
        ]
    )
    monkeypatch.setattr(geolocation, "_load_zcta_frame", lambda: frame)

    response = asyncio.run(geolocation.geolocate_zip("90210"))

    assert response.lat == 34.0901
    assert response.lon == -118.4065
    assert response.display_name == "ZCTA 90210"
    assert "INTPTLAT" not in (response.display_name or "")
    assert "{" not in (response.display_name or "")


def test_geolocate_zip_plus_four_curates_to_five_digits(monkeypatch) -> None:
    """ZIP+4 input resolves and curates to the 5-digit ZCTA name."""
    pd = __import__("pandas")
    from airunner_services.api.routes import geolocation

    frame = pd.DataFrame(
        [
            {
                "GEOID": "90210",
                "INTPTLAT": "34.0901",
                "INTPTLONG": "-118.4065",
            }
        ]
    )
    monkeypatch.setattr(geolocation, "_load_zcta_frame", lambda: frame)

    response = asyncio.run(geolocation.geolocate_zip("90210-1234"))

    assert response.display_name == "ZCTA 90210"


def test_snapshot_docs_disclose_pause_and_limits() -> None:
    """The VACUUM INTO pause disclosure cannot silently regress to blank."""
    from airunner_services.database import upgrade_backup

    module_doc = (upgrade_backup.__doc__ or "").lower()
    snapshot_doc = (upgrade_backup._snapshot_sqlite.__doc__ or "").lower()

    assert "vacuum into" in module_doc or "vacuum into" in snapshot_doc
    combined = module_doc + "\n" + snapshot_doc
    assert "busy timeout" in combined
    assert "no" in combined and "progress" in combined
    assert "journal" in combined or "writer" in combined or "wait" in combined
