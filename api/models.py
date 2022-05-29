from pydantic import BaseModel
from typing import Optional


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
    client: ContactModel
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



