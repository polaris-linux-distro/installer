
from enum import Enum

class Command(Enum):
    UP = 1,
    DOWN = 2,
    EXECUTE = 3
reversed = "\u001b[0m\u001b[7m"
reset = "\u001b[0m"

def renderMenu(menu, selected, getInput, clearCommand):
    while True:
        clearCommand()
        for i, menuitem in enumerate(menu):
            attrs = ['reverse', 'bold'] if (selected == i) else []
            text = reversed + menuitem[0] if (selected == i) else menuitem[0]
            text = text + reset
            print(text)
        command = getInput()
        match command: 
            case Command.DOWN:
                selected = (selected + 1) % len(menu)
            case Command.UP:
                selected = (selected - 1) % len(menu)
            case Command.EXECUTE:
                menu[selected][1]()
                break


