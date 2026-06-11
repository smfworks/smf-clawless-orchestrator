from clawmes import tui


def test_menu_renders_and_has_quit():
    menu = tui.render_menu()
    assert "Clawmes" in menu
    assert any(key == "quit" for _label, key in tui.MENU)
    assert any(key == "onboard" for _label, key in tui.MENU)


def test_color_disabled_without_tty():
    assert tui._bold("x") == "x"
