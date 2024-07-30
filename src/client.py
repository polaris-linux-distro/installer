import keyboard
import os
import time
from pymenu import Command, renderMenu

def mate_installer():
    print("hello")

def goodbye():
    print("goodbye")

dispatchMenu = [
    ['hello', hello],
    ['goodbye', goodbye]
]

selected = 0
def clear():
    os.system('clear')

def getInput():
    while True:
        key = keyboard.read_key() 
        time.sleep(0.15)
        match key:
            case "down":
                return Command.DOWN
            case "up":
                return Command.UP
            case "enter":
                return Command.EXECUTE

renderMenu(dispatchMenu, 0, getInput, clear)