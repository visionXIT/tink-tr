import asyncio
import copy
import datetime
import logging
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import starlette
from tinkoff.invest.grpc.instruments_pb2 import INSTRUMENT_ID_TYPE_FIGI
from tinkoff.invest.grpc.orders_pb2 import (
    ORDER_DIRECTION_SELL,
    ORDER_DIRECTION_BUY,
    ORDER_TYPE_MARKET,
)

from tinkoff.invest import InstrumentType

# from instruments_config.parser import instruments_config
from app.client import client
from app.settings import settings
from  app.utils.portfolio import get_position
from  app.utils.quotation import quotation_to_float

from  app.settings import settings

logging.basicConfig(
    level=settings.log_level,
    format="[%(levelname)-5s] %(asctime)-19s %(name)s:%(lineno)d: %(message)s",
)
logging.getLogger("tinkoff").setLevel(settings.tinkoff_library_log_level)
logger = logging.getLogger(__name__)

KOT = {
    "SBER": "BBG004730N88",
    "RUB": "RUB000UTSTOM",
    "SRU4": "FUTSBRF09240",
    "NGQ4": "FUTNG0824000"
}

KOT2 = {
    "BBG004730N88": "SBER",
    "RUB000UTSTOM": "RUB",
    "FUTSBRF09240": "SRU4",
    "FUTNG0824000": "NGQ4"
}


figi = KOT["NGQ4"]
figi_name = "NGQ4"
ii = None

q_limit = 1

templates = Jinja2Templates(directory='templates')
num_trades = 2
add_ticker = None
found_tickers = None
selected_type = None
bot_working = True

unsuccessful_trade = None

def correct_timezone(date):
    return date + datetime.timedelta(hours=3)

async def prepare_data():
    global ii
    print("prepared")
    try:
        ii= (
            await client.get_instrument(id_type=INSTRUMENT_ID_TYPE_FIGI, id=figi)
            # await client.get_instrument(id_type=INSTRUMENT_ID_TYPE_ISIN)
        ).instrument
    except:
        return 0

async def get_position_quantity() -> int:
    """
    Get quantity of the instrument in the position.
    :return: int - quantity
    """
    positions = (await client.get_portfolio(account_id=settings.account_id)).positions
    position = get_position(positions, figi)
    if position is None:
        return 0
    return int(quotation_to_float(position.quantity))

async def handle_sell():
    position_quantity = await get_position_quantity()
    if position_quantity > -q_limit:
        logger.info(
            f"Selling {position_quantity} shares. figi={figi}"
        )
        try:
            quantity = (q_limit + position_quantity) / ii.lot

            posted_order = await client.post_order(
                order_id=str(uuid4()),
                figi=figi,
                direction=ORDER_DIRECTION_SELL,
                quantity=int(quantity),
                order_type=ORDER_TYPE_MARKET,
                account_id=settings.account_id,
            )
        except Exception as e:
            logger.error(
                f"Failed to post sell order. figi={figi}. {e}")
            return 0
        ###
    else:
        logger.info("Have nothing to sell")

async def handle_buy():
    position_quantity = await get_position_quantity()
    if position_quantity < q_limit:
        quantity_to_buy = q_limit - position_quantity
        logger.info(
            f"Buying {quantity_to_buy} shares. figi={figi}"
        )
        try:
            quantity = quantity_to_buy / ii.lot
            print(quantity, ii.lot, position_quantity)
            posted_order = await client.post_order(
                order_id=str(uuid4()),
                figi=figi,
                direction=ORDER_DIRECTION_BUY,
                quantity=int(quantity),
                order_type=ORDER_TYPE_MARKET,
                account_id=settings.account_id,
            )
        except Exception as e:
            logger.error(
                f"Failed to post buy order. figi={figi}. {e}")
            return 0
        ###
    else:
        logger.info("Already have")
        
class Param(BaseModel):
    text: str

app = FastAPI()
@app.post("/")
async def get_alert(alert: Any = Body(None)):
    global ii, unsuccessful_trade
    
    logger.info("POST query")
    
    if client.client == None:
        await client.ainit()
    if ii == None:
        res = await prepare_data()
        if res == 0:
            await asyncio.sleep(2)
            res = await prepare_data()
            if res == 0:
                logger.error("Cannot prepare data")
                return
        
    # with open("log.txt", "a") as f:
    #     f.write(datetime.datetime.now().strftime() + "  " + str(alert) + " :: " + str(bot_working) + "\n")
    signal = alert.decode("ascii")
    res = None
    if bot_working:
        if signal== 'BUY':
            res = await handle_buy()
        elif signal == 'SELL':
            res = await handle_sell()
    if res == 0:
        unsuccessful_trade = signal  
        asyncio.create_task(wait_for_trade())

async def wait_for_trade():
    global unsuccessful_trade
    res = 0
    while unsuccessful_trade != None:
        now = datetime.datetime.now()
        print("FROM", now)
        
        if now.hour == 14 and now.minute in range(0, 6):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            print(a, a // 60, a % 60)
            await asyncio.sleep(a)
            
        elif (now.hour == 18 and now.minute >= 50):
            a = max(15 * 60 - (now.minute - 50) * 60 - now.second + 1, 0)
            print(a, a // 60, a % 60)
            await asyncio.sleep(a)

        elif (now.hour == 19 and now.minute <= 5):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            print(a, a // 60, a % 60)
            await asyncio.sleep(a)
            
        else:
            await asyncio.sleep(10)
            
        print("Waiting", unsuccessful_trade)
        
        if unsuccessful_trade== 'BUY':
            res = await handle_buy()
            if res == None:
                unsuccessful_trade = None
        elif unsuccessful_trade == 'SELL':
            res = await handle_sell()
            if res == None:
                unsuccessful_trade = None
    print("finished")

@app.get("/check")
async def health():    
    logger.info("check quiry")

    return "working" if bot_working else "not working"

@app.get("/break_waiting")
async def break_waiting():
    global unsuccessful_trade
    unsuccessful_trade = None
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)
    

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    global i, found_tickers
    
    logger.info("main query")
    
    if client.client == None:
        await client.ainit()
    if ii == None:
        await prepare_data()
            
    port = await client.get_portfolio(account_id=settings.account_id)
    orders = await client.get_operations(account_id=settings.account_id, 
                                         from_=datetime.datetime.now() - datetime.timedelta(days=num_trades),
                                         to=datetime.datetime.now())
    trades, inc = calc_trades(copy.copy(orders.operations))
    trades.reverse()
    orders.operations.reverse()
    opers = []
    
    def get_last_q(j):
        nonlocal opers
        
        for i in range(j - 1, -1, -1):
            if orders.operations[i].type in ["Покупка ценных бумаг", "Продажа ценных бумаг"]:
                return orders.operations[i]
            
    inc = 0
    for i in range(len(orders.operations)):
        oper = orders.operations[i]
        if oper.type == "Покупка ценных бумаг" or oper.type == "Продажа ценных бумаг":
            # print(oper.date, oper.quantity)
            if oper.quantity == q_limit or oper.quantity == q_limit * 2 or (get_last_q(i) and get_last_q(i).quantity / 2 + q_limit == oper.quantity):
                opers.append(oper)
                inc += quotation_to_float(oper.payment)
        elif oper.type == "Списание вариационной маржи" or oper.type == "Зачисление вариационной маржи":
            opers.append(oper)
            inc += quotation_to_float(oper.payment)

        elif oper.type == "Удержание комиссии за операцию":
            if len(opers) > 0 and orders.operations[i - 1].id == opers[-1].id and opers[-1].quantity in [q_limit, q_limit * 2]:
                opers.append(oper)
                inc += quotation_to_float(oper.payment)
        print(inc, oper.date)

    last = get_last_q(len(orders.operations))
    if last.type == "Продажа ценных бумаг":
        inc -= quotation_to_float(last.payment)
    
    opers.reverse()
    orders.operations = opers
    context = {
        "bot_working": bool(bot_working),
        "portfolio": port,
        "orders": orders,
        "settings": {
            "show_fees": True,
            "num_trades": num_trades
        },
        "f": {
            "correct_timezone": correct_timezone,
            "round": round,
            "len": len
        },
        "trades": trades,
        "result": inc,
        "q2f": quotation_to_float,
        "q_limit": q_limit,
        "figi": figi,
        "figi_name": figi_name,
        "figis": KOT,
        "figis2": KOT2,
        "add_ticker": add_ticker,
        "found_tickers": found_tickers,
        "selected_type": selected_type,
        "unsuccessful_trade": unsuccessful_trade
    }
    if not found_tickers or len(found_tickers) < 2:
        found_tickers = None
    
        
    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )
    
def calc_trades(trades):
    trades.reverse()
    res = []
    prev = None
    inc = 0
    num = 1
    
    def add_mark(prev, i, type):
        nonlocal num, inc
        inc += quotation_to_float(prev.payment) / 2 + \
            quotation_to_float(i.payment) / 2
        res.append({
                    "num": num,
                    "timeStart": correct_timezone(i.date).strftime("%Y-%m-%d %H:%M"),
                    "timeEnd": correct_timezone(prev.date).strftime("%Y-%m-%d %H:%M"),
                    "type": type,
                    "figi": i.figi,
                    "result": quotation_to_float(prev.payment) / 2 +
                            quotation_to_float(i.payment) / 2
        })
        num += 1
        
    for i in trades:
        if i.type == "Покупка ценных бумаг" and i.quantity == q_limit * 2:
            if prev != None and prev.figi == i.figi and prev.type == "Продажа ценных бумаг" :
                add_mark(prev, i, "Short")
            prev = i
        elif i.type == "Продажа ценных бумаг" and i.quantity == q_limit * 2:
            if prev != None and prev.figi == i.figi  and prev.type == "Покупка ценных бумаг" :
                add_mark(prev, i, "Long")
            prev = i
        elif i.type == "Удержание комиссии за операцию" or i.type == "Списание вариационной маржи" or i.type == "Зачисление вариационной маржи":
            inc += quotation_to_float(i.payment)

    
    return res, inc

    
@app.post("/change_num_trades")
async def change_num_trade(num: Annotated[int, Form()]):
    global num_trades
    print(num)
    num_trades = num
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)
    
   
@app.post("/change")
async def change():
    global bot_working
    
    logger.info("change query")
    
    bot_working = not bot_working
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)

@app.post('/exit_add_k')
async def exit_add_k():
    global add_ticker, found_tickers, selected_type
    add_ticker = found_tickers = selected_type = None
    
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)

@app.post("/add_k")
async def change_k(ticker: Annotated[str, Form()], type: Annotated[str, Form()]):
    global add_ticker, found_tickers, selected_type
    
    if ticker == " " or type == " ":
        return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)
    
    logger.info("main query")
    
    await check_client()
        
    selected_type = type

    i_type = None
    if type == 'share':
        i_type = InstrumentType.INSTRUMENT_TYPE_SHARE
    elif type == "futures":
        i_type = InstrumentType.INSTRUMENT_TYPE_FUTURES
    else:
        i_type = InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED
    
    add_ticker = ticker
    res = await client.find_instrument(query=ticker, instrument_kind=i_type, api_trade_available_flag=True)

    found_tickers = res.instruments
    if len(found_tickers) == 1:
        KOT[found_tickers[0].ticker] = found_tickers[0].figi
        KOT2[found_tickers[0].figi] = found_tickers[0].ticker
        add_ticker = None
        selected_type = None
    
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)

async def check_client():
    global ii
    if client.client == None:
        await client.ainit()
    if ii == None:
        await prepare_data()

@app.post("/change_q")
async def change(q: Annotated[str, Form()]):
    global q_limit
    
    logger.info("change query")
    
    q_limit = float(q)
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)

@app.post("/change_k")
async def change(k: Annotated[str, Form()]):
    global figi, figi_name
    
    figi = k
    figi_name = KOT2[figi]
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)