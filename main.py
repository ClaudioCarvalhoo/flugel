import datetime

from bs4 import BeautifulSoup
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException


def setupDriver():
    ## Setup chrome options
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Ensure GUI is off

    # Choose Chrome Browser
    driver = uc.Chrome(options=options)

    return driver


def getPage(driver, fromDate, toDate):
    url = (
        "https://flights.booking.com/flights/REC.AIRPORT-LON.CITY/?type=ROUNDTRIP&adults=1&cabinClass=ECONOMY&children="
        "&from=REC.AIRPORT&to=LON.CITY&fromCountry=BR&toCountry=GB&fromLocationName=Recife+%2F+Guararapes-Gilberto+Freyre+International+Airport&toLocationName=London"
        f"&depart={fromDate.year:04d}-{fromDate.month:02d}-{fromDate.day:02d}&return={toDate.year:04d}-{toDate.month:02d}-{toDate.day:02d}"
        "&sort=CHEAPEST&travelPurpose=leisure"
        "&aid=304142&label=gen173nr-1FCAEoggI46AdIM1gEaFCIAQGYAQm4ARfIAQ_YAQHoAQH4AQyIAgGoAgO4AtL__p8GwAIB0gIkN2Y0N2Y1YzItMTExMC00NTY0LWI4MGUtZTg2MmFhMzNjNzA42AIG4AIB"
    )
    print(url)
    driver.get(url)


def main():
    driver = setupDriver()
    getPage(driver, datetime.datetime(2023, 5, 1), datetime.datetime(2023, 10, 31))

    # Wait for it to load
    try:
        ignoreList = [ElementNotVisibleException, ElementNotSelectableException]
        wait = WebDriverWait(driver, timeout=5, poll_frequency=1, ignored_exceptions=ignoreList)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[class^='css-vxcmzt']")))
    except:
        soup = BeautifulSoup(driver.page_source, "lxml")
        print(soup.prettify())
    finally:
        soup = BeautifulSoup(driver.page_source, "lxml")
        priceDivs = soup.find_all("div", {"class": "css-vxcmzt"})
        prices = [float(div.text[1:]) for div in priceDivs]
        minPrice = min(prices)
        print(minPrice)

    driver.quit()


if __name__ == "__main__":
    main()
