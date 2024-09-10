import random

from discord.ext import commands
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from botInfo import HOSTER, USERS

import AutoPianoBookingUI
import functools
import time


link = 'https://w5.ab.ust.hk/wrm/app/login?path=/bookings/add/music-room/timetable'  # link to be opened


def set_path(room: int, day: int, time_slot: int, duration: int) -> [str]:
    """
    :param room: 1/2 (111/114)
    :param day: 1-7 (today:1, tmr:2, ...)
    :param time_slot: 1-30 (7am-21:30pm)
    :param duration: 1/2/3/4 (0/5/1/1.5/2 hours)
    :return: list of paths to be clicked

    # Day buttons: '/html/body/div/div/div[2]/div[2]/div/div/div[DAY]/div/button'
    # DAY: 1-7 (today:1, tmr:2, ...)

    # Time part buttons: '/html/body/div/div/div[2]/div[3]/div/div[ROOM]/div/div[1]/div/div/div/button[TIMEPART]'
    # ROOM: 2/3(111/114), TIMEPART: 1/2/3 (M/A/E)

    # Time slot buttons: '/html/body/div/div/div[2]/div[3]/div/div[ROOM]/div/div[2]/div[TIMEPART]/button[TIME]'
    # ROOM: 2/3(111/114), TIMEPART: 1/2/3 (M/A/E), TIME: 1-10/12/8 (M/A/E: 07/12/18)

    # Duration buttons: '/html/body/div[2]/div[3]/div/div[2]/div/button[DURATION]'
    # DURATION: 1/2/3/4 (0/5/1/1.5/2 hours)

    # Confirm button: '/html/body/div[2]/div[3]/div/div[3]/button[2]'
    # Accept button: '/html/body/div[3]/div[3]/div/div[3]/button[2]'
    """
    if not (1 <= room <= 2 and 1 <= day <= 7 and 1 <= time_slot <= 30 and 1 <= duration <= 4):
        raise ValueError("[AutoPianoBooking] set_path: Invalid input for booking options")

    room += 1
    time_part = 1 if time_slot <= 10 else 2 if time_slot <= 22 else 3
    session = time_slot if time_slot <= 10 else time_slot - 10 if time_slot <= 22 else time_slot - 22

    login_path = '/html/body/div/div/div/div/form/nav/li[2]/div[1]'
    login_username_path = '/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div/div[2]/div[2]/div/input[1]'
    login_password_path = '/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[3]/div/div[2]/input'
    duo_path = '/html/body/div/div/div[1]/div/div[2]/div[3]/button'
    day_path = f'/html/body/div/div/div[2]/div[2]/div/div/div[{day}]/div/button'
    time_part_path = f'/html/body/div/div/div[2]/div[3]/div/div[{room}]/div/div[1]/div/div/div/button[{time_part}]'
    time_slot_path = f'/html/body/div/div/div[2]/div[3]/div/div[{room}]/div/div[2]/div[{time_part}]/button[{session}]'
    duration_path = f'/html/body/div[2]/div[3]/div/div[2]/div/button[{duration}]'
    confirm_path = '/html/body/div[2]/div[3]/div/div[3]/button[2]'
    accept_path = '/html/body/div[3]/div[3]/div/div[3]/button[2]'

    return [login_path, login_username_path, login_password_path, duo_path, day_path, time_part_path, time_slot_path,
            duration_path, confirm_path, accept_path]


async def piano_system(bot: commands.Bot, message):
    async def run_blocking(blocking_func, *args, **kwargs):
        # Runs a blocking function in a non-blocking way
        func = functools.partial(blocking_func, *args, **kwargs)
        return await bot.loop.run_in_executor(None, func)

    def check_and_click(xpath: str, timeout=15) -> None:
        present = EC.presence_of_element_located(('xpath', xpath))  # check if button clickable
        WebDriverWait(driver, timeout).until(present)  # wait until the button is clickable, else return error
        button = driver.find_element('xpath', xpath)  # locate the corresponding button
        if not button.is_enabled():
            raise RuntimeError("Target button is not enabled")
        button.click()

    def check_and_write(xpath: str, text: str, timeout=300) -> None:
        present = EC.presence_of_element_located(('xpath', xpath))  # check if button clickable
        WebDriverWait(driver, timeout).until(present)  # wait until the button is clickable, else return error
        input_field = driver.find_element('xpath', xpath)  # locate the corresponding button
        if not input_field.is_enabled():
            raise RuntimeError("Target button is not enabled")
        input_field.send_keys(text+Keys.ENTER)

    def execute_booking() -> bool:
        while 1:  # infinite loop for repeated booking
            if book_now or time.ctime(time.time())[11:16] == '00:00':
                try:
                    driver.refresh()
                    for path in paths[4:]:
                        check_and_click(path)
                    return True
                except RuntimeError as err:
                    print(f"[AutoPianoBooking] execute_booking: {err}")
                    return False
            # if random.random() > 0.98:
            #     driver.refresh()
            continue

    try:
        menu = AutoPianoBookingUI.View(message.author)
        menu.message = await message.send(view=menu)
        await menu.wait()

        if menu.cancelled:
            return
        if not menu.finished:
            await message.channel.send("**> Input closed. You take too long!**")
            return

        book_now: bool = True if menu.action == 0 else False
        paths = set_path(menu.room, menu.day, menu.time_slot, menu.duration)

        # if HOSTER == "Mac":
        #     driver = webdriver.Safari()
        # elif HOSTER == "Windows":
        #     options = webdriver.EdgeOptions()
        #     options.add_argument('-inprivate')
        #     driver = webdriver.Edge(options=options)
        # else:
        #     raise ValueError("[AutoPianoBooking] piano_system: Invalid hoster")
        driver = webdriver.Chrome()
        driver.get(link)

        check_and_click(paths[0], 300)  # login
        check_and_write(paths[1], USERS[menu.user]["username"], 300)  # username
        check_and_write(paths[2], USERS[menu.user]["password"], 300)  # password
        await message.channel.send("**Please check your duo mobile!**")
        check_and_click(paths[3], 300)  # duo mobile

        if book_now:
            await message.channel.send("**Start waiting for 00:00 to book the piano room!**")

        if await run_blocking(execute_booking):
            await message.channel.send(f"**✔ Successfully booked [{menu.embed_text.description}]!**")
        else:
            await message.channel.send(f"**❌ Failed to book [{menu.embed_text.description}]!**")

        driver.close()
    except Exception as e:
        print(e)
        return False
