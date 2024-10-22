import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from constants import UNIFIED_CURRENCY, SUPPORTED_CURRENCY, CURRENCY_FILE

LINK = "https://www.oanda.com/currency-converter/en/?from=CNY&to=USD&amount=12"

baseCur_ctry_edit_path = \
    "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[1]/div[1]/div/div[2]/div/div/input"
baseCur_amt_path = \
    "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[1]/div[2]/div[1]/div/input"

targetCur_ctry_edit_path = \
    "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[1]/div/div[2]/div/div/input"
targetCur_amt_path = \
    "/html/body/div[1]/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[2]/div[1]/div/input"


def store_exchange_rate(curr_index: int, rate: float) -> None:
    ...
    # not done yet
    # with open(CURRENCY_FILE, 'r', encoding='utf8') as file:
    #     rate_dict = {line.split()[0]: [line.split()[1], line.split()[2]] for line in file}
    #
    # with open(CURRENCY_FILE, 'w+', encoding='utf8') as file:
    #     for curr, value in rate_dict.items():
    #         if curr == SUPPORTED_CURRENCY[curr_index]:
    #             file.write(f"{curr} {time.strftime('%d/%m', time.gmtime())} {rate}\n")
    #         else:
    #             file.write(f"{curr} {value[0]} {value[1]}\n")


def get_stored_exchange_rate(curr_index: int) -> str:
    with open(CURRENCY_FILE, 'r', encoding='utf8') as file:
        for line in file:
            curr, date, rate = line.split()
            if curr == SUPPORTED_CURRENCY[curr_index] and date == time.strftime("%d/%m", time.gmtime()):
                return line.split()[2]
        return ""  # currency not found


class ExchangeRateHandler:
    def __init__(self):
        self.currency = 0
        self.drive = None

    def change_currency(self, cur: str, path) -> None:
        present = EC.element_to_be_clickable(('xpath', path))  # check if button clickable
        WebDriverWait(self.driver, 180).until(present)
        text_box = self.driver.find_element('xpath', path)
        text_box.click()
        text_box.send_keys(cur)
        text_box.send_keys(Keys.DOWN)
        text_box.send_keys(Keys.ENTER)

    def enter_amount(self, amount: str, path) -> None:
        present = EC.element_to_be_clickable(('xpath', path))  # check if button clickable
        WebDriverWait(self.driver, 180).until(present)
        text_box = self.driver.find_element('xpath', path)
        # if HOSTER == "Mac":
        #     text_box.send_keys(Keys.BACKSPACE)
        #     text_box.send_keys(Keys.BACKSPACE)
        # elif HOSTER == "Windows":
        #     text_box.send_keys(Keys.CONTROL + "a")
        text_box.send_keys("\b\b\b" + amount)

    def get_amount(self, path) -> str:
        present = EC.presence_of_element_located(('xpath', path))  # check if button clickable
        WebDriverWait(self.driver, 180).until(present)
        text_box = self.driver.find_element('xpath', path)
        return text_box.get_attribute('value')

    def quit(self):
        self.driver.quit()

    def __call__(self, base: str, amount: str, target=UNIFIED_CURRENCY) -> str:
        stored_rate = get_stored_exchange_rate(target)
        if stored_rate:
            return str(float(amount) * float(stored_rate))

        if not (base in SUPPORTED_CURRENCY and target in SUPPORTED_CURRENCY):
            raise ValueError("Unsupported currency")
        elif base == target:
            return amount

        self.driver = webdriver.Chrome()
        self.driver.get(LINK)
        self.change_currency(base, baseCur_ctry_edit_path)
        self.change_currency(target, targetCur_ctry_edit_path)
        self.enter_amount(amount, baseCur_amt_path)
        time.sleep(0.5)
        result = self.get_amount(targetCur_amt_path)
        store_exchange_rate(target, float(result) / float(amount))  # Not done yet
        return result


def switch_currency(currency: str) -> str:
    currency = SUPPORTED_CURRENCY.index(currency)
    currency = (currency + 1) % len(SUPPORTED_CURRENCY)
    return SUPPORTED_CURRENCY[currency]


if __name__ == '__main__':
    a = ExchangeRateHandler()
    print(a('CNY', '10'))
    input()
