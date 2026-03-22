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

        assert "exactly one small clear straight-sided shot glass" in prompt
        assert "exactly three horizontal liquid layers only" in prompt
        assert "from bottom to top in this exact order" in prompt
        assert "no fourth layer" in prompt
        assert "no repeated bands" in prompt
        assert "no extra glass" in prompt
        assert "no second drink" in prompt

    def test_b52_uses_layered_shot_generation_mode(self):
        document = (
            "COCKTAIL 045 b-52. Категория: shot. "
            "Состав (мл): кофейный ликёр 20; сливочный ликёр 20; triple sec 20 (слои). "
            "Метод: билд слоями. Подача: shot."
        )

        mode = self.router._determine_image_generation_mode(document, "покажи b-52")

        assert mode == "layered_shot"

    def test_regular_cocktail_uses_default_generation_mode(self):
        document = (
            "COCKTAIL 005 негрони. Категория: spirit-forward. "
            "Состав (мл): джин 30; кампари 30; сладкий вермут 30. "
            "Подача: rocks, апельсин."
        )

        mode = self.router._determine_image_generation_mode(document, "покажи фото негрони")

        assert mode == "default"
