import os
import queue
from typing import Dict, List, Any
from models import ContactBitrixModel, DealBitrixModel, TaskBitrixModel, ContactModel, DealModel, TaskModel
from fast_bitrix24 import BitrixAsync
from isdayoff import DateType, ProdCalendar
import datetime
JSON = [dict(), list()]

# create connection to bitrix24 server


class Bitrix:
    def __init__(self, webhook):
        self.connection = BitrixAsync(webhook)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection = None


class BitrixContact(Bitrix, ContactBitrixModel):
    # def __int__(self, **kwargs):
    #     super(Bitrix).__init__(webhook=kwargs.get("webhook"))
    #     for key, values in kwargs.get("contact").items():
    #         self.key = values
    #     print(self.__dict__)

    async def find_contact(self, contact) -> int:
        json_data = self.get_json_find_contact(contact)
        method = "crm.contact.list"
        response = await self.connection.call(method, json_data, raw=True)

        if not response:
            contact_id = await self.create_contact(contact)
            return contact_id
        else:
            return response[0]["ID"]

    async def create_contact(self, contact) -> JSON:
        json_data = self.get_json_contact(contact)
        method = "crm.contact.add.json"
        response = await self.connection.call(method, json_data, raw=True)
        return response


class BitrixDeal(Bitrix, DealBitrixModel):
    message = []

    async def add_deal(self, deal) -> list[str]:
        deal_from_bitrix = await self.find_deal(deal)
        if deal_from_bitrix:
            if self.diff_dials(deal, deal_from_bitrix):
                self.message.append("deal have diffs")
                await self.update_deal(deal)
            else:
                self.message.append("deal have not diffs")
        else:
            await self.create_deal(deal)
        return self.message

    async def find_deal(self, deal) -> dict:
        json_data = self.get_json_for_find(deal)
        method = "crm.deal.list"
        deal_from_bitrix = await self.connection.call(method, json_data, raw=True)

        if deal_from_bitrix:
            self.message.append("Deal found")
            deal.id = deal_from_bitrix[0]['ID']
            return deal_from_bitrix[0]

    def diff_dials(self, deal, deal_from_bitrix) -> bool:
        if (deal_from_bitrix["CONTACT_ID"] != deal.client.id) \
                or (hash(deal_from_bitrix["COMMENTS"]) != hash(self.get_string_deal(deal))):
            return True

    async def create_deal(self, deal) -> JSON:
        json_data = self.get_json_for_add(deal)
        method = "crm.deal.add.json"
        result = await self.connection.call(method, json_data, raw=True)

        if result:
            self.message.append("Deal created")
            await self.update_deal_client(deal)
            return {"status": "200", "message": self.message}

    async def update_deal_client(self, deal) -> None:
        json_data = self.get_json_for_update_client_id(deal)
        method = "crm.deal.contact.items.set"
        result = await self.connection.call(method, json_data, raw=True)

        if result:
            self.message.append("client of dial updated")

    async def update_deal(self, deal) -> None:
        json_data = self.get_json_for_update(deal)
        method = "crm.deal.update.json"
        result = await self.connection.call(method, json_data, raw=True)

        if result:
            self.message.append("Deal updated")
            await self.update_deal_client(deal)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(self.message)


q = queue.Queue()


class BitrixTask(Bitrix, TaskBitrixModel):

    async def push_task_to_server(self, task) -> JSON:
        json_data = self.get_json_for_add(task)
        method = "tasks.task.add"
        response = await self.connection.call(method, json_data, raw=True)
        print(response)

    async def add_task(self, task):
        q.put(task)
        if await self.where_holidays():
            while not q.empty():
                task = q.get()
                response = await self.push_task_to_server(task)
                if not response:
                    q.put(task)
            return {"status": "200", "message": "Task added"}
        return {"status": "200", "message": "Task save to queue"}

    async def where_holidays(self):
        calendar = ProdCalendar()
        for delta_days in range(3):
            future_date = datetime.datetime.today() + datetime.timedelta(days=delta_days)
            print(future_date)
            future_date_bool = await calendar.date(date=future_date) == DateType.NOT_WORKING
            if future_date_bool:
                return future_date_bool
