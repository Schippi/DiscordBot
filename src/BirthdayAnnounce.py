
from datetime import datetime, timedelta
import time

from datetime import datetime
from dataclasses import dataclass
import time
import asyncio


@dataclass
class Birthday:
    name: str
    month: int
    day: int
    birth_year: int

# List of Birthday objects
birthdays_to_check = [
    Birthday(name="Bot", month=4, day=16, birth_year=2011),
    Birthday(name="Schippi", month=2, day=15, birth_year=1989),
    Birthday(name="Davaria", month=3, day=16, birth_year=1993),
    Birthday(name="Nemo", month=1, day=29, birth_year=1992),
    Birthday(name="Niu", month=7, day=20, birth_year=1994),
    Birthday(name="Peach", month=11, day=17, birth_year=1992),
    Birthday(name="Ari", month=2, day=9, birth_year=1989),
]

hardcoded_guild_id = 756476087701340160
#hardcoded_guild_id = 196211645289201665

# Function to check for upcoming birthdays
async def bday_loop(client):
    try:
        while not client._ready:
            await asyncio.sleep(3)
        await client.wait_until_ready();
    except Exception as e:
        print(e)

    while True:
        # Get today's date
        soon = datetime.now() + timedelta(days=31)
        soon_2 = datetime.now() + timedelta(days=15)

        # Check each birthday in the list
        for birthday in birthdays_to_check:
            # Check if today is the birthday and if it's 3 PM
            checked = None
            if soon.month == birthday.month and soon.day == birthday.day and soon.hour == 15:
                checked = soon
            elif soon_2.month == birthday.month and soon_2.day == birthday.day and soon_2.hour == 15:
                checked = soon_2

            if checked:
                # Calculate the age of the person
                age = checked.year - birthday.birth_year

                # Print the birthday message
                formatted_birthday = f"{birthday.day:02d}-{birthday.month:02d}-{birthday.birth_year}"
                printmsg = (f" {birthday.name}'s birthday is coming up in a months time! they will turn {age} on {formatted_birthday}!")
                guild = client.get_guild(hardcoded_guild_id)
                for c in guild.channels:
                    if "gift" in c.name.lower() and birthday.name.lower() in c.name.lower():
                        await c.send(printmsg)
                        break


        # Wait for 1 hour before checking again
        asyncio.sleep(60 * 60)  # Sleep for 1 hour