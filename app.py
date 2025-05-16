import pyfiglet
from colorama import Fore, init
from module.login import main as login
from dotenv import load_dotenv
import os

load_dotenv()
# Initialize colorama for auto reset of colors
init(autoreset=True)
# Author's name
author_name = os.getenv("author_name")

# Function to print the author's name in ASCII art
def print_author_name():
    # Generate the ASCII art for the author's name
    ascii_art = pyfiglet.figlet_format(author_name, font="slant")
    # Print the ASCII art with color
    print(Fore.YELLOW + ascii_art)

if __name__ == "__main__":
    print_author_name()
    login()
