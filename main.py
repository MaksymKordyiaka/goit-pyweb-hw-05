import asyncio
import logging
import websockets
import names
import json
import aiofiles
import aiopath
import aiohttp
import datetime


logging.basicConfig(level=logging.INFO)


class CurrencyAPI:
    def __init__(self):
        self.base_url = "https://api.privatbank.ua/p24api/exchange_rates"

    async def fetch_data(self, date):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}?&date={date.strftime('%d.%m.%Y')}") as response:
                    return await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Network error: {e}")
            return None

    async def get_exchange_rates(self, dates):
        tasks = [self.fetch_data(date) for date in dates]
        return await asyncio.gather(*tasks)


class Server:
    clients = set()
    api = CurrencyAPI()

    async def register(self, ws: websockets.WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: websockets.WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: websockets.WebSocketServerProtocol):
        await self.register(ws)
        try:
            async for message in ws:
                if message.startswith('exchange'):
                    try:
                        parts = message.split()
                        if len(parts) < 2 or len(parts) > 3:
                            await ws.send("Usage: exchange <days> [<currency1,currency2,...>]")
                            continue

                        days = int(parts[1])
                        if days <= 0 or days > 10:
                            await ws.send("Number of days should be between 1 and 10")
                            continue

                        currencies = ['EUR', 'USD']
                        if len(parts) == 3:
                            currencies = parts[2].split(',')

                        today = datetime.date.today()
                        dates = [today - datetime.timedelta(days=i) for i in range(days)]

                        exchange_rates = await self.api.get_exchange_rates(dates)
                        currency_data = []

                        for item in exchange_rates:
                            for excRate in item['exchangeRate']:
                                if excRate['currency'] in currencies:
                                    currency_data.append({'date': item['date'], **excRate})

                        response_message = json.dumps(currency_data, indent=2)

                        clients_copy = list(self.clients)
                        for client in clients_copy:
                            await client.send(response_message)

                        async with aiofiles.open(aiopath.Path('exchange.log'), 'a') as f:
                            await f.write(
                                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ws.remote_address} - exchange {days} {','.join(currencies)} - {response_message}\n")

                    except ValueError as e:
                        await ws.send(f"Error: {e}")
                else:
                    await self.send_to_clients(f"{ws.name}: {message}")
        except websockets.exceptions.ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())


