from darml.application.use_cases.list_targets import ListTargets


def test_lists_all_known_targets():
    ids = {t.id for t in ListTargets().execute()}
    assert {"esp32-s3", "stm32f4", "avr-mega328", "rpi4", "jetson-orin"}.issubset(ids)
