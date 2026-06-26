from .generateGears import entry as generateGears

commands = [
    generateGears,
]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
