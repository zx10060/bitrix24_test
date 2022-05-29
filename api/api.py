from fastapi import FastAPI

from work_with_bitrix24 import BitrixContact, BitrixDeal, BitrixTask
from models import DealModel, TaskModel
import os
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()
webhook = os.getenv("WEBHOOK")


@app.post("/api/deal/")
async def deals(deal: DealModel):
    bitrix_contact = BitrixContact(os.getenv("WEBHOOK"))
    deal.client.id = await bitrix_contact.find_contact(deal.client)
    if deal.client.id:
        bitrix_dial = BitrixDeal(os.getenv("WEBHOOK"))
        message = await bitrix_dial.add_deal(deal)
        if message:
            return {"status": "200", "message": message}
    else:
        return {"status": "501", "message": "Server error"}


@app.post("/api/task/")
async def tasks(task: TaskModel):
    bitrix_tasks = BitrixTask(os.getenv("WEBHOOK"))
    response = await bitrix_tasks.add_task(task)
    return response
    # return {"status": "501", "message": "Server error"}
