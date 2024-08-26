import asyncio
import copy
import datetime
import logging
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Body, FastAPI, Form, Request, Response
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
from app.utils.portfolio import get_position
from app.utils.quotation import quotation_to_float


from app.settings import settings

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
auth = None

templates = Jinja2Templates(directory='templates')
num_trades = 3
add_ticker = None
found_tickers = None
selected_type = None
bot_working = True
inverted = False
showAllTrades = True

unsuccessful_trade = None


def round2(r, g=2):
    return round(r, 3)


def correct_timezone(date):
    return date + datetime.timedelta(hours=3)


async def prepare_data():
    global ii
    print("prepared")
    try:
        ii = (
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
            with open("log.txt", "a") as f:
                f.write(datetime.datetime.now().strftime() +
                        "    ERROR " + str(e))
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
            with open("log.txt", "a") as f:
                f.write(datetime.datetime.now().strftime() +
                        "    ERROR " + str(e))
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

    with open("log.txt", "a") as f:
        f.write(datetime.datetime.now().strftime() + "  " +
                str(alert) + " :: " + str(bot_working) + "\n")
    signal = alert.decode("ascii")
    res = None
    if bot_working:
        if (signal == 'BUY' and not inverted) or (signal == "SELL" and inverted):
            res = await handle_buy()
        elif (signal == 'SELL' and not inverted) or (signal == "BUY" and inverted):
            res = await handle_sell()
    if res == 0:
        unsuccessful_trade = "BUY" if (signal == "BUY" and not inverted) or (
            signal == "SELL" and inverted) else "SELL"
        with open("e.txt", "a") as f:
            f.write(
                datetime.datetime.now().strftime() + "  " +
                str(unsuccessful_trade) + "\n"
            )
        asyncio.create_task(wait_for_trade())


async def wait_for_trade():
    global unsuccessful_trade
    res = 0
    while unsuccessful_trade != None:
        now = datetime.datetime.now()

        if now.hour == 14 and now.minute in range(0, 6):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            await asyncio.sleep(a)

        elif (now.hour == 18 and now.minute >= 50):
            a = max(15 * 60 - (now.minute - 50) * 60 - now.second + 1, 0)
            await asyncio.sleep(a)

        elif (now.hour == 19 and now.minute <= 5):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            await asyncio.sleep(a)

        else:
            await asyncio.sleep(10)

        print("Waiting", unsuccessful_trade)

        if unsuccessful_trade == 'BUY':
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
    global i, found_tickers, auth

    logger.info("main query")

    if client.client == None:
        await client.ainit()
    if ii == None:
        await prepare_data()

    port = await client.get_portfolio(account_id=settings.account_id)
    orders = await client.get_operations(account_id=settings.account_id,
                                         from_=datetime.datetime.now() - datetime.timedelta(days=num_trades),
                                         to=datetime.datetime.now())
    trades, inc, p = calc_trades(copy.copy(orders.operations))
    trades.reverse()
    orders.operations.reverse()
    opers = []

    if request.cookies.get("pass1"):
        auth = True
    else:
        auth = False

    def get_last_q(j, f=1):
        nonlocal opers, orders
        f = p if f == 1 else orders.operations
        for i in range(j - 1, -1, -1):
            if f[i].type in ["Покупка ценных бумаг", "Продажа ценных бумаг"]:
                return f[i]

    def get_first():
        for i in opers:
            if i.type in ["Покупка ценных бумаг", "Продажа ценных бумаг"]:
                return i

    inc = 0
    for i in range(len(p)):
        oper = p[i]
        if oper.type == "Покупка ценных бумаг" or oper.type == "Продажа ценных бумаг":
            if oper.quantity == q_limit or oper.quantity == q_limit * 2 or (get_last_q(i) and get_last_q(i).quantity / 2 + q_limit == oper.quantity):
                opers.append(oper)
                inc += quotation_to_float(oper.payment)
        elif oper.type == "Списание вариационной маржи" or oper.type == "Зачисление вариационной маржи":
            opers.append(oper)
            inc += quotation_to_float(oper.payment)

        elif oper.type == "Удержание комиссии за операцию":
            if len(opers) > 0 and p[i - 1].id == opers[-1].id and opers[-1].quantity in [q_limit, q_limit * 2]:
                opers.append(oper)
                inc += quotation_to_float(oper.payment)
    last = get_last_q(len(p))
    if last and get_first() and last.type == get_first().type:
        inc -= quotation_to_float(last.payment)
    opers = []

    for i in range(len(orders.operations)):
        oper = orders.operations[i]
        if oper.type == "Покупка ценных бумаг" or oper.type == "Продажа ценных бумаг":
            if oper.quantity == q_limit or oper.quantity == q_limit * 2 or (get_last_q(i, 2) and get_last_q(i, 2).quantity / 2 + q_limit == oper.quantity):
                opers.append(oper)
                # inc += quotation_to_float(oper.payment)
        elif oper.type == "Списание вариационной маржи" or oper.type == "Зачисление вариационной маржи":
            opers.append(oper)
            # inc += quotation_to_float(oper.payment)

        elif oper.type == "Удержание комиссии за операцию":
            if len(opers) > 0 and orders.operations[i - 1].id == opers[-1].id:
                opers.append(oper)
                # inc += quotation_to_float(oper.payment)
        # print(inc, oper.date)

    opers.reverse()
    if not showAllTrades:
        orders.operations = opers
    else:
        orders.operations.reverse()
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
            "round": round2,
            "len": len
        },
        "inverted": inverted,
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
        "unsuccessful_trade": unsuccessful_trade,
        "auth": auth if settings.password else True,
        "show_all_trades": showAllTrades
    }
    if not found_tickers or len(found_tickers) < 2:
        found_tickers = None

    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


def calc_trades(trades):
    trades.reverse()
    res = []
    p = []
    prev = None
    inc = 0
    num = 1

    def add_mark(prev, i, type):
        nonlocal num, inc, p
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
            if prev != None and prev.figi == i.figi and prev.type == "Продажа ценных бумаг":
                add_mark(prev, i, "Short")
            prev = i
            p.append(prev)
        elif i.type == "Продажа ценных бумаг" and i.quantity == q_limit * 2:
            if prev != None and prev.figi == i.figi and prev.type == "Покупка ценных бумаг":
                add_mark(prev, i, "Long")
            prev = i
            p.append(prev)
        elif i.type == "Удержание комиссии за операцию" or i.type == "Списание вариационной маржи" or i.type == "Зачисление вариационной маржи":
            inc += quotation_to_float(i.payment)
            p.append(i)

    return res, inc, p


@app.post("/change_show_all_trades")
async def changeShowAllTrades():
    global showAllTrades

    showAllTrades = not showAllTrades
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/make_trade")
async def make_trade(trade: Annotated[str, Form()]):
    print(trade)

    if trade == "buy":
        await handle_buy()
    elif trade == "sell":
        await handle_sell()

    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/pass")
async def passs(s: Annotated[str, Form()], response: Response):
    res = RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)
    if settings.password == s:
        res.set_cookie(key="pass1", value=True, expires=60 * 30)
    return res


@app.post("/change_num_trades")
async def change_num_trade(num: Annotated[int, Form()]):
    global num_trades
    num_trades = num
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post('/change_inv')
def ch():
    global inverted
    inverted = not inverted
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
