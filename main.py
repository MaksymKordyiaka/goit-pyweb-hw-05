import datetime
import json

import aiohttp
import asyncio
import sys

class CurrencyAPI:
    def __init__(self):
        self.base_url = "https://api.privatbank.ua/p24api/exchange_rates"

    async def fetch_data(self, date):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}?&date={date.strftime('%d.%m.%Y')}") as response:
                    return await response.json()
        except aiohttp.ClientError as e:
            print(f"Network error: {e}")

    async def get_exchange_rates(self, dates):
        tasks = [self.fetch_data(date) for date in dates]
        return await asyncio.gather(*tasks)

async def main(days):
    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(days)]
    api = CurrencyAPI()
    exchange_rates = await api.get_exchange_rates(dates)
    return exchange_rates

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <number_of_days>")
        sys.exit(1)
    try:
        days = int(sys.argv[1])
        if days <= 0 or days > 10:
            raise ValueError("Number of days should be between 1 and 10")
    except ValueError as e:
        print("Invalid input:", e)
        sys.exit(1)
    result = asyncio.run(main(days))

    currency_data = []
    for item in result:
        for exchRate in item['exchangeRate']:
            if exchRate['currency'] == 'EUR' or exchRate['currency'] == 'USD':
                currency_data.append(exchRate)
    formatted_result = json.dumps(currency_data, indent=2)
    print(formatted_result)

