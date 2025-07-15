from src.config import get_all_models_and_providers

def test_get_all_models_and_providers():
    models = get_all_models_and_providers()
    assert isinstance(models, list)