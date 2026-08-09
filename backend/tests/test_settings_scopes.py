from app.modules.settings.schemas import InstagramAppInput


def test_insights_scope_is_requested_by_default() -> None:
    field = InstagramAppInput.model_fields["scopes"]
    assert field.default_factory is not None
    assert "instagram_business_manage_insights" in field.default_factory()
