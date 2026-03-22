from services.router import RequestRouter


class TestImagePrompts:
    def setup_method(self):
        self.router = RequestRouter()

    def test_negroni_prompt_is_strict(self):
        document = (
            "COCKTAIL 005 негрони. Категория: spirit-forward. "
            "Состав (мл): джин 30; кампари 30; сладкий вермут 30. "
            "Метод: стир/билд. Подача: rocks, апельсин. Вкус: горько-сладкий, травяной."
        )

        prompt = self.router._create_cocktail_image_prompt(document, "покажи фото негрони").lower()

        assert "one classic negroni" in prompt
        assert "exactly one rocks glass" in prompt
        assert "no whipped cream" in prompt
        assert "no creamy topping" in prompt
        assert "no extra glass" in prompt

    def test_b52_prompt_requires_single_shot(self):
        document = (
            "COCKTAIL 045 b-52. Категория: shot. "
            "Состав (мл): кофейный ликёр 20; сливочный ликёр 20; triple sec 20 (слои). "
            "Метод: билд слоями. Подача: shot. Вкус: сладкий, кофейно-сливочный."
        )

        prompt = self.router._create_cocktail_image_prompt(document, "покажи b-52").lower()

        assert "exactly one small clear shot glass" in prompt
        assert "exactly three distinct liquid layers only" in prompt
        assert "no second glass" in prompt
        assert "no extra drink" in prompt
