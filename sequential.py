import datetime
import math

import yaml
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException


def getConfig():
    with open("config.yaml", "r") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        return config


def daterange(fromDate, toDate):
    for n in range(int((toDate - fromDate).days + 1)):
        yield fromDate + datetime.timedelta(n)


def stringToDate(dateString):
    datetimeObj = datetime.datetime.strptime(dateString, "%d/%m/%Y")
    return datetimeObj.date()


def setupDriver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Ensure GUI is off
    driver = uc.Chrome(options=options)
    return driver


def getPage(driver, departDate, returnDate):
    url = (
        "https://flights.booking.com/flights/REC.AIRPORT-LON.CITY/?type=ROUNDTRIP&adults=1&cabinClass=ECONOMY&children="
        "&from=REC.AIRPORT&to=LON.CITY&fromCountry=BR&toCountry=GB&fromLocationName=Recife+%2F+Guararapes-Gilberto+Freyre+International+Airport&toLocationName=London"
        f"&depart={departDate.year:04d}-{departDate.month:02d}-{departDate.day:02d}&return={returnDate.year:04d}-{returnDate.month:02d}-{returnDate.day:02d}"
        "&sort=CHEAPEST&travelPurpose=leisure"
        "&aid=304142&label=gen173nr-1FCAEoggI46AdIM1gEaFCIAQGYAQm4ARfIAQ_YAQHoAQH4AQyIAgGoAgO4AtL__p8GwAIB0gIkN2Y0N2Y1YzItMTExMC00NTY0LWI4MGUtZTg2MmFhMzNjNzA42AIG4AIB"
    )
    driver.get(url)


def durationAsString(departDate, returnDate):
    return departDate.strftime("%d/%m/%Y") + " - " + returnDate.strftime("%d/%m/%Y")


def printPrice(departDate, returnDate, price):
    print(durationAsString(departDate, returnDate) + ": £" + str(price))


def printError(departDate, returnDate):
    print(durationAsString(departDate, returnDate) + ": ERROR")


def getMinPriceOfDay(driver, departDate, returnDate):
    getPage(driver, departDate, returnDate)

    try:
        ignoreList = [ElementNotVisibleException, ElementNotSelectableException]
        wait = WebDriverWait(driver, timeout=30, poll_frequency=1, ignored_exceptions=ignoreList)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[class^='css-vxcmzt']")))

        soup = BeautifulSoup(driver.page_source, "lxml")
        priceDivs = soup.find_all("div", {"class": "css-vxcmzt"})
        prices = [float(div.text[1:]) for div in priceDivs]
        minPrice = min(prices)
        printPrice(departDate, returnDate, minPrice)
        return minPrice
    except:
        soup = BeautifulSoup(driver.page_source, "lxml")
        printError(departDate, returnDate)
        with open("output1.html", "w") as file:
            file.write(str(soup))
        return 9999


def main():
    config = getConfig()

    driver = setupDriver()

    minPrice = 9999
    minPriceDates = []

    futures = []

    # Iterate all possible depart dates
    for departDate in daterange(stringToDate(config["departDate"]["from"]), stringToDate(config["departDate"]["to"])):
        # Iterate all possible return dates
        for returnDate in daterange(
            stringToDate(config["returnDate"]["from"]), stringToDate(config["returnDate"]["to"])
        ):
            price = getMinPriceOfDay(driver, departDate, returnDate)
            if price < minPrice:
                minPrice = price
                minPriceDates = [durationAsString(departDate, returnDate)]
            elif math.isclose(price, minPrice):
                minPriceDates.append(durationAsString(departDate, returnDate))

    print("Lowest price: £" + str(minPrice) + " for dates " + str(minPriceDates))

    driver.quit()


if __name__ == "__main__":
    main()
