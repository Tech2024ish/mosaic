from app.services.google_auth_service import create_google_state, validate_google_state


def test_google_oauth_state_is_signed_and_validated() -> None:
    state = create_google_state()

    assert validate_google_state(state)
    assert not validate_google_state(f"{state}tampered")


def test_google_oauth_state_rejects_unrelated_values() -> None:
    assert not validate_google_state("")
    assert not validate_google_state("not-a-google-state")
