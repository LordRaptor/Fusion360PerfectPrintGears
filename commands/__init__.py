from .generateGears import entry as generateGears
from .calcGearTrain import entry as calcGearTrain

commands = [
    generateGears,
    calcGearTrain,
]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
