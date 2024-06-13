from typst_telegram.render import Context


class TestContext:

    def test_init(self, ppi: int = 300):
        """Dummy test for testing CI workflows."""
        context = Context(dpi=ppi)
        assert context.dpi == ppi
