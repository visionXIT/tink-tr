import logging.handlers
import os
import sqlite3
import asyncio
import copy
import datetime
import logging
import random
from typing import Annotated, Any, Literal
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
from tinkoff.invest.grpc.operations_pb2 import OperationType

from tinkoff.invest import InstrumentType

# from instruments_config.parser import instruments_config
from app.client import client
from app.settings import settings
from app.utils.portfolio import get_position
from app.utils.quotation import quotation_to_float
from app.utils.profit_calculator import ProfitCalculator

from apscheduler.schedulers.asyncio import AsyncIOScheduler


from app.settings import settings

schedule = AsyncIOScheduler()


def correct_timezone(date: datetime.datetime) -> datetime.datetime:
    """Apply timezone correction (+3 hours for Moscow time)"""
    return date + datetime.timedelta(hours=3)


@schedule.scheduled_job('interval', seconds=10)
async def check_stop_loss():
    global last_order_price, last_order

    logger.debug("CHECK STOP LOSS START")
    if stop_loss_diff == 0 or not stop_loss:
        logger.debug("STOP LOSS IS DISABLED")
        return
    if last_order_price:
        current_price = await client.get_last_price(figi)
        logger.debug(
            f"CURRENT PRICE {current_price}, LAST ORDER PRICE {last_order_price}, STOP LOSS DIFF {stop_loss_diff}")
        if last_order.direction == ORDER_DIRECTION_BUY and last_order_price - current_price > stop_loss_diff:
            await handle_operation("SELL" if not stop_loss_closes_position else "CLOSE", "STOP LOSS FROM BUY")
            logger.info(f"STOP LOSS {datetime.datetime.now()}")
        elif last_order.direction == ORDER_DIRECTION_SELL and current_price - last_order_price > stop_loss_diff:
            await handle_operation("BUY" if not stop_loss_closes_position else "CLOSE", "STOP LOSS FROM SELL")
            logger.info(f"STOP LOSS {datetime.datetime.now()}")
    logger.debug("CHECK STOP LOSS END")


@schedule.scheduled_job('interval', hours=24)
async def remove_log_file():
    os.remove("log.txt")

# Only start the scheduler if not in testing mode
if __name__ == "__main__" and not os.getenv('TESTING'):
    schedule.start()


logging.basicConfig(
    level=settings.log_level,
    format="[%(levelname)-5s] %(asctime)-19s %(name)s:%(lineno)d: %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            "log.txt", maxBytes=5 * 1024),
        logging.StreamHandler()
    ]
)
logging.getLogger("tinkoff").setLevel(settings.tinkoff_library_log_level)
logger = logging.getLogger(__name__)

con = sqlite3.connect("trading.db")
cur = con.cursor()
quotes = cur.execute("SELECT * FROM quoutes").fetchall()
settings_bot = cur.execute("SELECT * FROM settings LIMIT 1").fetchone()
cur.close()

KOT = dict()
KOT2 = dict()

for q in quotes:
    KOT[q[0]] = q[1]
    KOT2[q[1]] = q[0]

figi = KOT.get(settings_bot[6])
figi_name = settings_bot[6]
ii = None

q_limit = settings_bot[1]
auth = None

templates = Jinja2Templates(directory='templates')
num_trades = 10
add_ticker = None
found_tickers = None
selected_type = None
bot_working = True
inverted = True if settings_bot[2] == 1 else False
showAllTrades = True
piramid = False
maxAmount = 0
stop_loss = False
stop_loss_diff = 0

stop_loss_closes_position = False

last_order_price = 0
last_order = None

unsuccessful_trade = None

error = None

work_on_time = True if settings_bot[3] == 1 else False
time_start = datetime.time.fromisoformat(
    settings_bot[4]) if settings_bot[4] and settings_bot[4] != "None" else None
time_end = datetime.time.fromisoformat(
    settings_bot[5]) if settings_bot[5] and settings_bot[5] != "None" else None

task_for_closing_position = None


async def wait_for_close():
    global task_for_closing_position, unsuccessful_trade
    now = correct_timezone(datetime.datetime.now()).time()

    if time_end == None or not work_on_time:
        task_for_closing_position.cancel()
        return

    logger.debug(f"WAITING {now}, {time_end}, {time_start}, {work_on_time}")

    if work_on_time and time_end != None and now < time_end:
        t = None
        try:
            t = time_end.hour * 3600 + time_end.minute * 60 + \
                time_end.second - now.hour * 3600 - now.minute * 60 - now.second
        except Exception as e:
            logger.error(f"Error {e}")
            await asyncio.sleep(10)
            await wait_for_close()
            return
        logger.debug(f"WAITING FOR {t}")

        await asyncio.sleep(t)
        logger.debug(f":: {now}, {time_end}, {time_start}, {work_on_time}")

        if work_on_time:
            res = await handle_operation("CLOSE")
            logger.error(res)
            if res == 0:
                unsuccessful_trade = 'CLOSE'
                logger.error(" Unsucceful trade " +
                             str(unsuccessful_trade))
                await wait_for_trade(0)

    elif work_on_time and time_end != None and now > time_end:
        logger.debug("WAITING 2")
        await asyncio.sleep((24 - now.hour) * 3600 + (60 - now.minute) * 60 + (60 - now.second) + 10 * 3600)
        await wait_for_close()
        return

    logger.debug("waited")
    await asyncio.sleep(60)
    await wait_for_close()

if time_end:
    task_for_closing_position = asyncio.create_task(wait_for_close())


def save_settings():
    cur = con.cursor()
    cur.execute("UPDATE settings SET lot=?, inverted=?, work_on_time=?, start_work=?, end_work=?, set_q=? WHERE id = 1",
                (q_limit, 1 if inverted else 0, 1 if work_on_time else 0, str(time_start), str(time_end), figi_name))
    con.commit()
    cur.close()


def round2(r, g=2):
    return round(r, 3)


def correct_timezone(date):
    return date + datetime.timedelta(hours=3)


async def prepare_data():
    global ii
    logger.debug("Instrument data preparation")
    try:
        ii = (
            await client.get_instrument(id_type=INSTRUMENT_ID_TYPE_FIGI, id=figi)
        ).instrument
    except Exception as e:
        logger.error(f"Failed to prepare instrument data: {e}")
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


async def handle_operation(type: Literal["BUY", "SELL", "CLOSE"], id="0"):
    logger.debug(f"Handling operation {type} id: {id}")
    global last_order_price

    if type == "BUY":
        res = await handle_buy(id)
    elif type == "SELL":
        res = await handle_sell(id)
    elif type == "CLOSE":
        res = await handle_close(id)
    else:
        logger.error(f"Unknown operation type: {type}")
        return 0

    if res is None:
        current_price = await client.get_last_price(figi)
        last_order_price = current_price
    return res


async def handle_sell(id="0"):
    global error, last_order_price, last_order
    logger.debug("HANDLE SELL START")
    position_quantity = await get_position_quantity()

    if (piramid and position_quantity > -maxAmount) or (not piramid and position_quantity > -q_limit):

        try:
            if piramid:
                quantity = q_limit if position_quantity - q_limit > - \
                    maxAmount else (maxAmount + position_quantity)

                if position_quantity > 0:
                    quantity = position_quantity + \
                        (q_limit if q_limit < maxAmount else maxAmount)

                quantity /= ii.lot
            else:
                quantity = (q_limit + position_quantity) / ii.lot

            logger.info(
                id + f" Selling {quantity} shares. figi={figi}"
            )

            posted_order = await client.post_order(
                order_id=str(uuid4()),
                figi=figi,
                direction=ORDER_DIRECTION_SELL,
                quantity=int(quantity),
                order_type=ORDER_TYPE_MARKET,
                account_id=settings.account_id,
            )

            last_order = posted_order

            logger.info(id + " " + str(posted_order.lots_requested) + " " +
                        str(posted_order.figi) + " " + str(posted_order.direction))
        except Exception as e:
            error = str(e)
            logger.error(
                id + f" Failed to post sell order. figi={figi}. {e}")
            return 0
        ###
    else:
        logger.info(id + " Already in position")
    logger.debug("HANDLE SELL END")


async def handle_buy(id="0"):
    global error, last_order_price, last_order
    logger.debug("HANDLE BUY START")
    position_quantity = await get_position_quantity()

    if (not piramid and position_quantity < q_limit) or (piramid and position_quantity < maxAmount):

        try:
            if piramid:
                quantity = q_limit if position_quantity + \
                    q_limit < maxAmount else (maxAmount - position_quantity)

                if position_quantity < 0:
                    quantity = -position_quantity + \
                        (q_limit if q_limit < maxAmount else maxAmount)

            else:
                quantity = q_limit - position_quantity
            quantity /= ii.lot

            logger.info(
                id + f" Buying {quantity} shares. figi={figi}"
            )

            posted_order = await client.post_order(
                order_id=str(uuid4()),
                figi=figi,
                direction=ORDER_DIRECTION_BUY,
                quantity=int(quantity),
                order_type=ORDER_TYPE_MARKET,
                account_id=settings.account_id,
            )

            logger.info(id + " " + str(posted_order.lots_requested) + " " +
                        str(posted_order.figi) + " " + str(posted_order.direction))

            last_order = posted_order
        except Exception as e:
            error = e
            logger.error(
                id + f" Failed to post buy order. figi={figi}. {e}")
            return 0
        ###
    else:
        logger.info(id + " Already have enough")
    logger.debug("HANDLE BUY END")


async def handle_close(id="0"):
    global error, last_order_price, last_order
    logger.debug("HANDLE CLOSE START")
    position_quantity = await get_position_quantity()
    if position_quantity != 0:
        quantity_to_buy = abs(position_quantity)
        logger.info(
            id + f" Closing {quantity_to_buy} shares. figi={figi}"
        )
        try:
            quantity = quantity_to_buy / ii.lot

            posted_order = await client.post_order(
                order_id=str(uuid4()),
                figi=figi,
                direction=ORDER_DIRECTION_BUY if position_quantity < 0 else ORDER_DIRECTION_SELL,
                quantity=int(quantity),
                order_type=ORDER_TYPE_MARKET,
                account_id=settings.account_id,
            )

            last_order_price = None
            last_order = None

            logger.info(id + " " + str(posted_order.lots_requested) + " " +
                        str(posted_order.figi) + " " + str(posted_order.direction))
        except Exception as e:
            error = e
            logger.error(
                id + f" Failed to post close order. figi={figi}. {e}")
            return 0
        ###
    else:
        logger.info(id + " Already closed")
    logger.debug("HANDLE CLOSE END")


class Param(BaseModel):
    text: str


app = FastAPI()


@app.post("/")
async def get_alert(request: Request, alert: Any = Body(None)):
    global ii, unsuccessful_trade

    id = str(random.randint(100, 10000))

    if alert == None:
        logger.error("None alert " + str(await request.body()))
        return

    signal = str(alert.decode("ascii"))
    logger.info(id + " POST query " + str(signal) + " " + str(inverted))
    signal = signal.rstrip()

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

    res = None
    logger.info(str(id) + " " + str(work_on_time) + " " +
                str(time_start) + " " + str(time_end))
    if bot_working and \
            ((work_on_time and time_start and time_end and (
                (time_start < time_end and time_start <= correct_timezone(
                    datetime.datetime.now()).time() <= time_end)
                or (time_start > time_end and (time_start <= correct_timezone(datetime.datetime.now()).time() or correct_timezone(datetime.datetime.now()).time() <= time_end))
            )) or not work_on_time or not time_start or not time_end):

        if (signal == 'BUY' and not inverted) or (signal == "SELL" and inverted):
            res = await handle_operation("BUY", id)
            logger.info(str(id) + " BUY")
        elif (signal == 'SELL' and not inverted) or (signal == "BUY" and inverted):
            res = await handle_operation("SELL", id)
            logger.info(str(id) + " SELL")
        else:
            logger.error(str(id) + " UNKNOWN SIGNAL " + signal)
    if res == 0:
        unsuccessful_trade = "BUY" if (signal == "BUY" and not inverted) or (
            signal == "SELL" and inverted) else "SELL"
        logger.error(id + " Unsucceful trade " + str(unsuccessful_trade))

        asyncio.create_task(wait_for_trade(id))


async def wait_for_trade(id="0"):
    global unsuccessful_trade
    res = 0
    while unsuccessful_trade != None:
        now = correct_timezone(datetime.datetime.now())

        if now.hour == 14 and now.minute in range(0, 6):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            logger.error(id + " For " + str(a))

            await asyncio.sleep(a)

        elif (now.hour == 18 and now.minute >= 50):
            a = max(15 * 60 - (now.minute - 50) * 60 - now.second + 1, 0)
            logger.error(id + " For " + str(a))

            await asyncio.sleep(a)

        elif (now.hour == 19 and now.minute <= 5):
            a = max(5 * 60 - now.minute * 60 - now.second + 1, 0)
            logger.error(id + " For " + str(a))

            await asyncio.sleep(a)

        else:
            await asyncio.sleep(10)

        logger.error(id + " Waiting " + str(unsuccessful_trade))

        if unsuccessful_trade == 'BUY':
            res = await handle_operation("BUY", id)
            if res == None:
                unsuccessful_trade = None
        elif unsuccessful_trade == 'SELL':
            res = await handle_operation("SELL", id)
            if res == None:
                unsuccessful_trade = None
        elif unsuccessful_trade == 'CLOSE':
            res = await handle_operation("CLOSE", id)
            if res == None:
                unsuccessful_trade = None
    logger.info(id + " finished")


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

    start_time = datetime.datetime.now() - datetime.timedelta(days=num_trades)
    start_time = start_time.replace(hour=0, minute=0)

    port = await client.get_portfolio(account_id=settings.account_id)
    orders = await client.get_operations(account_id=settings.account_id,
                                         from_=start_time,
                                         to=datetime.datetime.now())
    trades, inc, p = calc_trades(copy.copy(orders.operations))
    trades.reverse()

    orders.operations.reverse()

    if request.cookies.get("pass1"):
        auth = True
    else:
        auth = False

    def get_last_q(j, f=1):
        nonlocal opers, orders
        f = p if f == 1 else orders.operations
        for i in range(j - 1, -1, -1):
            if f[i].operation_type in [OperationType.OPERATION_TYPE_BUY, OperationType.OPERATION_TYPE_SELL]:
                return f[i]

    opers = []

    for i in range(len(orders.operations)):
        oper = orders.operations[i]
        if oper.operation_type == OperationType.OPERATION_TYPE_BUY or oper.operation_type == OperationType.OPERATION_TYPE_SELL:
            if oper.quantity == q_limit or oper.quantity == q_limit * 2 or (get_last_q(i, 2) and get_last_q(i, 2).quantity / 2 + q_limit == oper.quantity):
                opers.append(oper)
        elif oper.operation_type == OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN or oper.operation_type == OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN:
            opers.append(oper)

        elif oper.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
            if len(opers) > 0 and orders.operations[i - 1].id == opers[-1].id:
                opers.append(oper)

    if not showAllTrades:
        orders.operations = opers
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
        "show_all_trades": showAllTrades,
        "error": error,
        "time_start": time_start,
        "time_end": time_end,
        "work_on_time": work_on_time,
        "maxam": maxAmount,
        "piramid": piramid,
        "stop_loss": stop_loss,
        "stop_loss_diff": stop_loss_diff,
        "stop_loss_closes_position": stop_loss_closes_position
    }

    if not found_tickers or len(found_tickers) < 2:
        found_tickers = None

    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


def calc_trades(operations):
    """
    Calculate trades using the enhanced ProfitCalculator with auto-detected starting positions
    Returns trades in the old format for compatibility
    """
    calculator = ProfitCalculator()
    # Use the enhanced method that automatically detects starting positions
    trades, total_profit, processed_operations, starting_positions = calculator.process_operations_with_auto_positions(
        operations)

    # Convert to old format for compatibility
    res = []
    for i, trade in enumerate(trades):
        res.append({
            "num": i + 1,
            "timeStart": trade.entry_time.strftime("%Y-%m-%d %H:%M"),
            "timeEnd": trade.exit_time.strftime("%Y-%m-%d %H:%M"),
            "type": trade.direction.title(),
            "figi": trade.figi,
            "quantity": trade.quantity,
            "pt1": trade.entry_price,
            "pt2": trade.exit_price,
            "result": trade.net_profit,
            "gross_profit": trade.gross_profit,
            "fees": trade.fees
        })

    return res, total_profit, processed_operations


@app.post("/change_work_on_time")
async def change_work_on_time():
    global work_on_time
    work_on_time = not work_on_time
    save_settings()

    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_time")
async def change_time(ts: Annotated[datetime.time, Form()] = None, te: Annotated[datetime.time, Form()] = None):
    global time_start, time_end, task_for_closing_position
    time_start = ts
    time_end = te
    save_settings()

    if task_for_closing_position:
        task_for_closing_position.cancel()

    if time_end:
        task_for_closing_position = asyncio.create_task(wait_for_close())

    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_show_all_trades")
async def changeShowAllTrades():
    global showAllTrades

    showAllTrades = not showAllTrades
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_stop_loss_closes_position")
async def changeStopLossClosesPosition():
    global stop_loss_closes_position

    stop_loss_closes_position = not stop_loss_closes_position
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_stop_loss")
async def changeStopLoss():
    global stop_loss

    stop_loss = not stop_loss
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_stop_loss_diff")
async def changeStopLossDiff(diff: Annotated[float, Form()]):
    global stop_loss_diff
    stop_loss_diff = diff
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/make_trade")
async def make_trade(trade: Annotated[str, Form()]):
    if trade == "buy":
        await handle_operation("BUY")
    elif trade == "sell":
        await handle_operation("SELL")
    elif trade == "close":
        await handle_operation("CLOSE")

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


@app.post("/change_pir")
async def change_pir():
    global piramid
    piramid = not piramid
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_max_am")
async def change_maxam(maxam: Annotated[int, Form()]):
    global maxAmount
    maxAmount = maxam
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post('/change_inv')
async def ch():
    global inverted
    inverted = not inverted
    save_settings()
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change")
async def change():
    global bot_working
    bot_working = not bot_working
    save_settings()
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
    if len(found_tickers) == 1 and KOT.get(found_tickers[0].ticker) == None:
        KOT[found_tickers[0].ticker] = found_tickers[0].figi
        KOT2[found_tickers[0].figi] = found_tickers[0].ticker
        add_ticker = None
        selected_type = None
        cur = con.cursor()
        cur.execute(
            f"INSERT INTO quoutes(name, figi) VALUES('{found_tickers[0].ticker}', '{found_tickers[0].figi}')")
        con.commit()
        cur.close()

    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


async def check_client():
    global ii
    if client.client == None:
        await client.ainit()
    if ii == None:
        await prepare_data()


@app.post("/change_q")
async def change1(q: Annotated[str, Form()]):
    global q_limit

    q_limit = float(q)

    save_settings()
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.post("/change_k")
async def change2(k: Annotated[str, Form()]):
    global figi, figi_name

    figi = k
    figi_name = KOT2[figi]
    save_settings()
    return RedirectResponse("/", status_code=starlette.status.HTTP_302_FOUND)


@app.get("/api/profit-analysis")
async def get_profit_analysis(days: int = 30, enhanced: bool = True):
    """Get detailed profit analysis for the specified number of days"""
    if client.client is None:
        await client.ainit()

    try:
        import datetime
        moscow_tz = __import__('pytz').timezone('Europe/Moscow')
        end_date = datetime.datetime.now(moscow_tz)
        start_date = end_date - datetime.timedelta(days=days)

        if enhanced:
            # Use enhanced method with current positions
            result = await client.get_enhanced_profit_analysis(
                settings.account_id, start_date, end_date, use_current_positions=True
            )

            if 'error' in result:
                return {"error": result['error']}

            trades = result['trades']
            total_profit = result['total_profit']

            # Get analysis report
            analysis_report = result['analysis_report']

            return {
                "method": "enhanced",
                "total_profit": total_profit,
                "trades_count": len(trades),
                "winning_trades": len([t for t in trades if t.net_profit > 0]),
                "losing_trades": len([t for t in trades if t.net_profit < 0]),
                "average_profit_per_trade": total_profit / len(trades) if trades else 0,
                "starting_positions": result['starting_positions'],
                "current_positions": result['current_positions'],
                "data_quality": analysis_report['data_quality'],
                "recommendations": analysis_report['recommendations'],
                "problematic_trades_count": len(result['problematic_trades']),
                "validation_result": result['validation_result'],
                "recent_trades": [
                    {
                        "entry_time": t.entry_time.isoformat(),
                        "exit_time": t.exit_time.isoformat(),
                        "direction": t.direction,
                        "quantity": t.quantity,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                        "gross_profit": t.gross_profit,
                        "fees": t.fees,
                        "net_profit": t.net_profit
                    } for t in trades[-10:]  # Last 10 trades
                ]
            }
        else:
            # Use traditional method for comparison
            operations_response = await client.get_historical_data(
                account_id=settings.account_id,
                days=days
            )

            if not operations_response:
                return {"error": "Failed to get operations data"}

            calculator = ProfitCalculator()
            trades, total_profit, _ = calculator.process_operations(
                operations_response.operations)

            return {
                "method": "traditional",
                "total_profit": total_profit,
                "trades_count": len(trades),
                "winning_trades": len([t for t in trades if t.net_profit > 0]),
                "losing_trades": len([t for t in trades if t.net_profit < 0]),
                "average_profit_per_trade": total_profit / len(trades) if trades else 0,
                "recent_trades": [
                    {
                        "entry_time": t.entry_time.isoformat(),
                        "exit_time": t.exit_time.isoformat(),
                        "direction": t.direction,
                        "quantity": t.quantity,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                        "gross_profit": t.gross_profit,
                        "fees": t.fees,
                        "net_profit": t.net_profit
                    } for t in trades[-10:]  # Last 10 trades
                ]
            }

    except Exception as e:
        logger.error(f"Error in profit analysis: {e}")
        return {"error": str(e)}


@app.get("/api/period-profit")
async def get_period_profit(start_date: str, end_date: str, starting_balance: float = 0.0):
    """Get profit analysis for a specific period"""
    if client.client is None:
        await client.ainit()

    try:
        import datetime
        start_dt = datetime.datetime.fromisoformat(start_date)
        end_dt = datetime.datetime.fromisoformat(end_date)

        operations_response = await client.get_operations_for_period(
            account_id=settings.account_id,
            start_date=start_dt,
            end_date=end_dt
        )

        if not operations_response:
            return {"error": "Failed to get operations data"}

        calculator = ProfitCalculator()
        period_profit = calculator.calculate_period_profit(
            operations_response.operations,
            start_dt,
            end_dt,
            starting_balance
        )

        return {
            "start_date": period_profit.start_date.isoformat(),
            "end_date": period_profit.end_date.isoformat(),
            "starting_balance": period_profit.starting_balance,
            "ending_balance": period_profit.ending_balance,
            "total_profit": period_profit.total_profit,
            "total_fees": period_profit.total_fees,
            "net_profit": period_profit.net_profit,
            "profit_percentage": period_profit.profit_percentage,
            "trades_count": period_profit.trades_count,
            "winning_trades": period_profit.winning_trades,
            "losing_trades": period_profit.losing_trades
        }

    except Exception as e:
        logger.error(f"Error in period profit analysis: {e}")
        return {"error": str(e)}


@app.get("/api/enhanced-profit-analysis")
async def get_enhanced_profit_analysis(days: int = 30):
    """Get enhanced profit analysis with comprehensive position tracking"""
    if client.client is None:
        await client.ainit()

    try:
        import datetime
        moscow_tz = __import__('pytz').timezone('Europe/Moscow')
        end_date = datetime.datetime.now(moscow_tz)
        start_date = end_date - datetime.timedelta(days=days)

        result = await client.get_enhanced_profit_analysis(
            settings.account_id, start_date, end_date, use_current_positions=True
        )

        if 'error' in result:
            return {"error": result['error']}

        trades = result['trades']
        analysis_report = result['analysis_report']

        return {
            "summary": {
                "total_profit": result['total_profit'],
                "trades_count": len(trades),
                "winning_trades": len([t for t in trades if t.net_profit > 0]),
                "losing_trades": len([t for t in trades if t.net_profit < 0]),
                "average_profit_per_trade": result['total_profit'] / len(trades) if trades else 0,
                "method_used": result['method_used']
            },
            "positions": {
                "starting_positions": result['starting_positions'],
                "current_positions": result['current_positions'],
                "starting_positions_count": len(result['starting_positions']),
                "current_positions_count": len(result['current_positions'])
            },
            "data_quality": analysis_report['data_quality'],
            "recommendations": analysis_report['recommendations'],
            "problematic_trades": [
                {
                    "trade_id": issue['trade'].trade_id,
                    "figi": issue['trade'].figi,
                    "net_profit": issue['trade'].net_profit,
                    "severity": issue['severity'],
                    "issues": issue['issues']
                } for issue in result['problematic_trades']
            ],
            "validation_result": result['validation_result'],
            "position_history": {
                figi: [
                    {
                        "date": change['date'].isoformat() if change['date'] else None,
                        "position": change['position'],
                        "operation_type": change['operation_type'],
                        "quantity": change.get('quantity', 0),
                        "crosses_zero": change.get('crosses_zero', False)
                    } for change in history[:10]  # Limit to first 10 changes per FIGI
                ] for figi, history in result['position_history'].items()
            },
            "trades": [
                {
                    "trade_id": t.trade_id,
                    "figi": t.figi,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "direction": t.direction,
                    "quantity": t.quantity,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "gross_profit": t.gross_profit,
                    "fees": t.fees,
                    "net_profit": t.net_profit,
                    "variation_margin": t.variation_margin
                } for t in trades
            ]
        }

    except Exception as e:
        logger.error(f"Error in enhanced profit analysis: {e}")
        return {"error": str(e)}


@app.get("/api/profit-diagnostics")
async def get_profit_diagnostics(days: int = 30):
    """Diagnose profit calculation issues and provide recommendations"""
    if client.client is None:
        await client.ainit()

    try:
        import datetime
        moscow_tz = __import__('pytz').timezone('Europe/Moscow')
        end_date = datetime.datetime.now(moscow_tz)
        start_date = end_date - datetime.timedelta(days=days)

        diagnosis = await client.diagnose_profit_calculation_issues(
            settings.account_id, start_date, end_date
        )

        if 'error' in diagnosis:
            return {"error": diagnosis['error']}

        return {
            "diagnosis": {
                "severity": diagnosis['severity'],
                "comparison": diagnosis['comparison'],
                "issues_detected": diagnosis['issues_detected'],
                "recommendations": diagnosis['recommendations'],
                "specific_recommendations": diagnosis['specific_recommendations']
            },
            "problematic_trades": [
                {
                    "trade_id": issue['trade'].trade_id,
                    "figi": issue['trade'].figi,
                    "net_profit": issue['trade'].net_profit,
                    "severity": issue['severity'],
                    "issues": issue['issues']
                } for issue in diagnosis['problematic_trades']
            ],
            "validation_result": diagnosis['validation_result']
        }

    except Exception as e:
        logger.error(f"Error in profit diagnostics: {e}")
        return {"error": str(e)}


@app.get("/api/position-analysis")
async def get_position_analysis(days: int = 30):
    """Get detailed position analysis for the specified period"""
    if client.client is None:
        await client.ainit()

    try:
        import datetime
        moscow_tz = __import__('pytz').timezone('Europe/Moscow')
        end_date = datetime.datetime.now(moscow_tz)
        start_date = end_date - datetime.timedelta(days=days)

        # Get operations for the period
        operations_response = await client.get_operations_for_period(
            settings.account_id, start_date, end_date
        )

        if not operations_response:
            return {"error": "Failed to get operations data"}

        calculator = ProfitCalculator()

        # Analyze starting positions
        position_analysis = calculator.analyze_starting_positions(
            operations_response.operations
        )

        # Calculate starting positions using current positions
        starting_positions = await client.calculate_starting_positions(
            settings.account_id, start_date, end_date
        )

        # Get current positions
        current_positions_response = await client.get_positions(account_id=settings.account_id)
        current_positions = {}
        if current_positions_response:
            if hasattr(current_positions_response, 'securities'):
                for security in current_positions_response.securities:
                    current_positions[security.figi] = int(security.balance)
            if hasattr(current_positions_response, 'futures'):
                for future in current_positions_response.futures:
                    current_positions[future.figi] = int(future.balance)

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "positions": {
                "starting_positions": starting_positions,
                "current_positions": current_positions,
                "instruments_count": len(set(list(starting_positions.keys()) + list(current_positions.keys())))
            },
            "position_analysis": {
                figi: {
                    "first_operation": analysis["first_operation"],
                    "total_operations": analysis["total_operations"],
                    "possible_scenarios": analysis["possible_scenarios"]
                } for figi, analysis in position_analysis.items()
            }
        }

    except Exception as e:
        logger.error(f"Error in position analysis: {e}")
        return {"error": str(e)}
