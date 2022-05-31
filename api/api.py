import os
from fastapi import FastAPI
from dotenv import load_dotenv

from .work_with_bitrix24 import BitrixDeal, BitrixTask


app = FastAPI()
load_dotenv()
WEBHOOK = os.getenv("WEBHOOK")


@app.post("/api/deal/")
async def deals(deal: BitrixDeal):
    # bitrix_contact = BitrixContact(bitrix_contact, deal.client)
    # client = BitrixContact(deal.client)
    deal.client.id = await deal.client.find_contact(deal.client)
    if deal.client.id:
        message = await deal.add_deal(deal)
        if message:
            return {"status": "200", "message": message}
    else:
        return {"status": "501", "message": "Server error"}


@app.post("/api/task/")
async def tasks(task: BitrixTask):
    response = await task.add_task(task=task)
    return response
    # return {"status": "501", "message": "Server error"}
