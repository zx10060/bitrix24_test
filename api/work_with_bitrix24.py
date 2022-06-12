import os
import queue
import datetime
from dotenv import load_dotenv
from isdayoff import DateType, ProdCalendar
from fast_bitrix24 import BitrixAsync
from pydantic import BaseModel
from typing import Optional, Union, List, Dict

load_dotenv()
WEBHOOK = os.getenv("WEBHOOK")


class BitrixServer:
    def __init__(self):
        self.__connection = BitrixAsync(WEBHOOK)

    def __enter__(self):
        return self.__connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__connection = None


class ContactModel(BaseModel):
    """
    {
        "name": "Jon",
        "surname": "Karter",
        "phone": "+77777777777",
        "adress": "st. Mira, 287, Moscow"
        }
    """
    name: str
    surname: str
    phone: str
    address: str
    id: Optional[int] = None


class ContactBitrixModel(ContactModel):
    def get_json_contact(self, contact):
        json_data = {"fields": {
            "NAME": contact.name,
            "LAST_NAME": contact.surname,
            "OPENED": "Y",
            "TYPE_ID": "CLIENT",
            "SOURCE_ID": "SELF",
            "PHONE": [{"VALUE": contact.phone, "VALUE_TYPE": "WORK"}],
            "ADDRESS": contact.address
        },
            "params": {"REGISTER_SONET_EVENT": "Y"}}
        return json_data

    def get_json_find_contact(self, contact):
        """
        "crm.contact.list",
        {
            filter: {"TYPE_ID": "CLIENT"},
            select: ["ID", "NAME", "LAST_NAME", "TYPE_ID", "SOURCE_ID"]
        }
        :param contact data from response to server
        :returns [ID]
        """
        json_data = {"filter": {
            "PHONE": contact.phone},
            "select": ["ID"]
        }
        return json_data


class BitrixContact(ContactBitrixModel):
    async def find_contact(self, contact) -> int:

        json_data = self.get_json_find_contact(contact)
        method = "crm.contact.list"

        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)

        if not response:
            contact_id = await self.create_contact(contact)
            return contact_id
        else:
            return response[0]["ID"]

    async def create_contact(self, contact) -> Union[Dict, List]:
        json_data = self.get_json_contact(contact)
        method = "crm.contact.add.json"
        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)
        return response


class DealModel(BaseModel):
    """
        {
            "title": "title",
            "description": "Some description",
            "client": Contact,
            "products": ["Candy", "Carrot", "Potato"],
            "delivery_adress": "st. Mira, 211, Ekaterinburg",
            "delivery_date": "2021-01-01:16:00",
            "delivery_code": "#232nkF3fAdn"
        }
    """
    title: str
    description: str
    client: BitrixContact
    products: list
    delivery_address: str
    delivery_date: str
    delivery_code: str
    id: Optional[int] = None


class DealBitrixModel(DealModel):
    def get_json_for_find(self, deal):
        json_data = {"filter": {"TITLE": deal.delivery_code},
                     "select": ["CONTACT_ID", "COMMENTS"]
                     }
        return json_data

    def get_string_deal(self, deal):
        deal_str = f"TITLE: {deal.title},\n" \
                   f"DESCRIPTION: {deal.description},\n" \
                   f"PRODUCTS: {deal.products},\n" \
                   f"DELIVERY_ADDRESS: {deal.delivery_address},\n" \
                   f"DELIVERY_DATE: {deal.delivery_date}\n"
        return deal_str

    def get_json_for_add(self, deal):
        json_data = {"fields": {
            "TITLE": deal.delivery_code,
            "CONTACT_ID": deal.client.id,
            "COMMENTS": self.get_string_deal(deal)},
            "params": {"REGISTER_SONET_EVENT": "Y"}
        }
        return json_data

    def get_json_for_update_client_id(self, deal):
        json_data = {"id": deal.id,
                     "items": [{"CONTACT_ID": deal.client.id}]}
        return json_data

    def get_json_for_update(self, deal):
        json_data = {
            "id": deal.id,
            "fields": {
                "TITLE": deal.delivery_code,
                "CONTACT_ID": deal.client.id,
                "COMMENTS": self.get_string_deal(deal)
            },
            "params": {"REGISTER_SONET_EVENT": "Y"}
        }
        return json_data


class BitrixDeal(DealBitrixModel):
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

        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)

        if response:
            self.message.append("Deal found")
        deal.id = response[0]['ID']
        return response[0]

    def diff_dials(self, deal, deal_from_bitrix) -> bool:
        if (deal_from_bitrix["CONTACT_ID"] != deal.client.id) \
                or (hash(deal_from_bitrix["COMMENTS"]) != hash(self.get_string_deal(deal))):
            return True

    async def create_deal(self, deal) -> Union[Dict, List]:
        json_data = self.get_json_for_add(deal)
        method = "crm.deal.add.json"
        async with BitrixServer() as server:
            async with server.call(method, json_data, raw=True) as response:
                response = await response

        if response:
            self.message.append("Deal created")
            await self.update_deal_client(deal)
            return {"status": "200", "message": self.message}

    async def update_deal_client(self, deal) -> None:
        json_data = self.get_json_for_update_client_id(deal)
        method = "crm.deal.contact.items.set"

        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)

        if response:
            self.message.append("client of dial updated")

    async def update_deal(self, deal) -> None:
        json_data = self.get_json_for_update(deal)
        method = "crm.deal.update.json"

        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)

        if response:
            self.message.append("Deal updated")
            await self.update_deal_client(deal)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(self.message)


# TODO Move Redis
q = queue.Queue()


class TaskFieldsModel(BaseModel):
    """{"TITLE": title, "RESPONSIBLE_ID": 1}"""
    TITLE: str
    RESPONSIBLE_ID: str


class TaskModel(BaseModel):
    """{"fields": {...}}"""
    fields: TaskFieldsModel


class TaskBitrixModel(TaskModel):
    def get_json_for_add(self, task):
        # title = "task for test"
        json_data = {"fields": {
            "TITLE": task.fields.TITLE,
            "RESPONSIBLE_ID": 1}
        }
        return json_data


class BitrixTask(TaskBitrixModel):

    async def push_task_to_server(self, task) -> Union[Dict, List]:
        json_data = self.get_json_for_add(task)
        method = "tasks.task.add"
        with BitrixServer() as server:
            response = await server.call(method, json_data, raw=True)
        return response

    async def add_task(self, task):
        q.put(task)
        if await self.where_holidays():
            while not q.empty():
                task = q.get()
                response = await self.push_task_to_server(task)
            if not response:
                q.put(task)
                return {"status": "200", "message": "Task save to queue"}

        return {"status": "200", "message": "Task added"}

    async def where_holidays(self):
        async with Calendar() as calendar:
            for delta_days in range(5):
                future_date = datetime.datetime.today() + datetime.timedelta(days=delta_days)
                future_date_bool = await calendar.date(date=future_date) == DateType.NOT_WORKING
                # print(future_date, future_date_bool)
                if future_date_bool:
                    return future_date_bool


class Calendar(ProdCalendar):
    async def __aenter__(self):
        self.conn = super()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()
