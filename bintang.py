import logging
import signal
import random
from time import sleep

from gpiozero import LED
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_GARAGE_DOOR_OPENER, CATEGORY_SWITCH


logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")


class GarageLock(Accessory):
    category = CATEGORY_SWITCH

    def __init__(self, garage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        garage.set_lock(self)
        self.locked = False
        self.add_preload_service("Switch").configure_char(
            "On", setter_callback=self.set_state
        )
        self.lock()

    def set_state(self, state):
        self.locked = state == 1
        logging.info(f"Garate lock: {self.locked}")

    def lock(self):
        self.get_service("Switch").get_characteristic("On").set_value(1)
        self.locked = True


class GarageDoor(Accessory):
    """Garage door opener"""

    category = CATEGORY_GARAGE_DOOR_OPENER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._led = LED(17)
        self._lock = None
        self.add_preload_service("GarageDoorOpener").configure_char(
            "TargetDoorState", setter_callback=self.change_state
        )

    def change_state(self, value):
        if self._lock and self._lock.locked:
            logging.info(f"Garage is locked, setting value {value}")
            self.get_service("GarageDoorOpener").get_characteristic(
                "CurrentDoorState"
            ).set_value(value)
            return

        logging.info("Garage door: %s", value)

        self._led.on()
        sleep(2)
        self._led.off()

        self.get_service("GarageDoorOpener").get_characteristic(
            "CurrentDoorState"
        ).set_value(value)

    def set_lock(self, lock):
        self._lock = lock


def get_bridge(driver):
    bridge = Bridge(driver, "Bridge")
    garage = GarageDoor(driver, "Garage")
    garage_lock = GarageLock(garage, driver, "GarageLock")
    bridge.add_accessory(garage)
    bridge.add_accessory(garage_lock)
    return bridge


driver = AccessoryDriver(port=51826, persist_file="bintang.state")
driver.add_accessory(accessory=get_bridge(driver))
signal.signal(signal.SIGTERM, driver.signal_handler)
driver.start()
