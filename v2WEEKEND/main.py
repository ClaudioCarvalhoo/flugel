import ctypes

libgcc_s = ctypes.CDLL("libgcc_s.so.1")

import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import yaml
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException


class Trip:
    def __init__(self, type, departDate, returnDate, locationFrom, locationTo):
        self.type = type
        self.departDate = departDate
        self.returnDate = returnDate
        self.locationFrom = locationFrom
        self.locationTo = locationTo
        self.price = None

    def locationFromName(self):
        return self.locationFrom["name"]

    def locationToName(self):
        return self.locationTo["name"]

    def departDateStr(self):
        return self.departDate.strftime("%d/%m")

    def returnDateStr(self):
        return self.returnDate.strftime("%d/%m")

    def datesSummary(self):
        return f"{self.departDateStr()}-{self.returnDateStr()} ({self.type})"

    def __str__(self):
        return f"{self.locationFromName()}/{self.locationToName()} {self.datesSummary()} {'£' + str(self.price) if self.price else 'ERROR'}"


class BookingScraper:
    def __init__(self):
        self.driver = None
        self.setupDriver()

    def setupDriver(self):
        while self.driver is None:
            try:
                options = uc.ChromeOptions()
                options.add_argument("--headless")  # Ensure GUI is off
                driver = uc.Chrome(options=options, version_main=110)
                self.driver = driver
            except:
                print("Issue setting up driver - retrying")

    def getPage(self, trip):
        url = (
            f"https://flights.booking.com/flights/{trip.locationFrom['code']}.{trip.locationFrom['type']}-{trip.locationTo['code']}.{trip.locationTo['type']}/?type=ROUNDTRIP"
            "&adults=1&cabinClass=ECONOMY&children="
            f"&from={trip.locationFrom['code']}.{trip.locationFrom['type']}&to={trip.locationTo['code']}.{trip.locationTo['type']}"
            f"&fromCountry={trip.locationFrom['country']}&toCountry={trip.locationTo['country']}&fromLocationName={trip.locationFrom['name']}&toLocationName={trip.locationTo['name']}"
            f"&depart={trip.departDate.year:04d}-{trip.departDate.month:02d}-{trip.departDate.day:02d}"
            f"&return={trip.returnDate.year:04d}-{trip.returnDate.month:02d}-{trip.returnDate.day:02d}"
            "&sort=CHEAPEST&travelPurpose=leisure"
            "&aid=304142&label=gen173nr-1FCAEoggI46AdIM1gEaFCIAQGYAQm4ARfIAQ_YAQHoAQH4AQyIAgGoAgO4AtL__p8GwAIB0gIkN2Y0N2Y1YzItMTExMC00NTY0LWI4MGUtZTg2MmFhMzNjNzA42AIG4AIB"
        )
        self.driver.get(url)

    def processTrip(self, trip):
        lock = Lock()
        if self.driver is None:
            self.setupDriver()
        self.getPage(trip)
        try:
            ignoreList = [ElementNotVisibleException, ElementNotSelectableException]
            wait = WebDriverWait(self.driver, timeout=30, poll_frequency=1, ignored_exceptions=ignoreList)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[class^='css-vxcmzt']")))

            soup = BeautifulSoup(self.driver.page_source, "lxml")
            priceDivs = soup.find_all("div", {"class": "css-vxcmzt"})
            prices = [float(div.text[1:]) for div in priceDivs]
            minPrice = min(prices)

            # Thread-safety is fun! :)
            lock.acquire()
            trip.price = minPrice
            lock.release()
        except:
            # Save error for debugging
            soup = BeautifulSoup(self.driver.page_source, "lxml")
            with open("error.html", "w") as file:
                file.write(str(soup))
        finally:
            print(trip)
            self.driver.quit()
            self.driver = None


class ExcelBuilder:
    def __init__(self):
        self.dataframes = {}

    def buildTripsDataframe(self, locationsFrom, trips):
        for locationFrom in locationsFrom:
            tripsFromCurrent = list(filter(lambda trip: trip.locationFromName() == locationFrom["name"], trips))
            df = pd.DataFrame(
                {
                    "locationTo": [trip.locationToName() for trip in tripsFromCurrent],
                    "date": [trip.datesSummary() for trip in tripsFromCurrent],
                    "price": [trip.price for trip in tripsFromCurrent],
                }
            )
            df = df.pivot(index="date", columns="locationTo", values="price")
            self.dataframes[locationFrom["name"]] = df

    def saveToExcelFiles(self):
        for locationFromName in self.dataframes:
            writer = pd.ExcelWriter(f"{locationFromName}.xlsx", engine="xlsxwriter")
            self.dataframes[locationFromName].to_excel(
                writer,
                sheet_name="Prices",
                index=True,
                na_rep="N/A",
                index_label=" ",
            )

            workbook = writer.book
            worksheet = writer.sheets["Prices"]
            format = workbook.add_format({"num_format": "£0.00"})

            worksheet.set_column(0, 0, 30, format)
            worksheet.set_column(1, 999, 20, format)

            blanksFormat = workbook.add_format()
            worksheet.conditional_format("A1:XFD1048576", {"type": "blanks", "format": blanksFormat})

            missingFormat = workbook.add_format({"bg_color": "#DB1F48"})
            worksheet.conditional_format(
                "B1:XFD1048576", {"type": "text", "criteria": "containing", "value": "N/A", "format": missingFormat}
            )

            lowestPricesFormat = workbook.add_format({"bg_color": "#00D100"})
            worksheet.conditional_format(
                "B1:XFD1048576", {"type": "bottom", "value": "10", "format": lowestPricesFormat}
            )

            lowPricesFormat = workbook.add_format({"bg_color": "#7EC8E3"})
            worksheet.conditional_format(
                "B1:XFD1048576", {"type": "cell", "criteria": "<=", "value": 20, "format": lowPricesFormat}
            )

            writer.close()


def getConfig():
    with open("config.yaml", "r") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        return config


def buildTrips(numberOfWeekends, locationsFrom, locationsTo):
    result = []

    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)

    for _ in range(numberOfWeekends):
        saturday = friday + datetime.timedelta(days=1)
        sunday = friday + datetime.timedelta(days=2)
        for locationTo in locationsTo:
            for locationFrom in locationsFrom:
                result.append(Trip("FRI-SUN", friday, sunday, locationFrom, locationTo))
                result.append(Trip("SAT-SUN", saturday, sunday, locationFrom, locationTo))
        friday += datetime.timedelta(days=7)
    return result


def main():
    config = getConfig()

    trips = buildTrips(config["numberOfWeekends"], config["locationsFrom"], config["locationsTo"])
    with ThreadPoolExecutor(max_workers=12) as executor:
        for trip in trips:
            bookingScraper = BookingScraper()
            executor.submit(bookingScraper.processTrip, trip)

    excelBuilder = ExcelBuilder()
    excelBuilder.buildTripsDataframe(config["locationsFrom"], trips)
    excelBuilder.saveToExcelFiles()


if __name__ == "__main__":
    main()
