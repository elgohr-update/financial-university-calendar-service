import logging
from datetime import datetime

from aiohttp import ClientSession, ClientError
import pytz
from ujson import loads

from calendar_fu.cal_lib import ICalendar, IEvent
from calendar_fu.schemas import Pair

log = logging.getLogger(__name__)

DATE_FORMAT = "%Y.%m.%d"
PAIR_SCHEMA = Pair()


class EmptySchedule(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


def get_dates():
    now = datetime.now()
    if now.month < 8:
        return (
            datetime(now.year, 1, 8).strftime(DATE_FORMAT),
            datetime(now.year, 6, 30).strftime(DATE_FORMAT),
        )
    else:
        return (
            datetime(now.year, 8, 15).strftime(format),
            datetime(now.year + 1, 1, 31).strftime(format),
        )


def create_calendar(
    rasp: list, url: str = "", exclude: set = None, subgroups_include: dict = None
):
    if subgroups_include is None:
        subgroups_include = {}
    if exclude is None:
        exclude = set()
    exclude.update(subgroups_include.keys())

    calendar = ICalendar(
        name="Расписание Университета",
        description="Расписание Финансового Университета schedule.fa.ru",
        prodid="-//FU_calendar//FU calendar 1.0//RU",
        color="teal",
        url=url,
        refresh_time="PT4H",
        timezone=pytz.timezone("Europe/Moscow"),
    )

    for pair in rasp:
        if str(pair["discipline_id"]) in exclude and subgroups_include.get(
            str(pair["discipline_id"]), 0
        ) != str(pair["stream_id"]):
            continue

        # try:
        #     pair = PAIR_SCHEMA.load(pair)
        # except ValidationError:
        #     log.warning("Error in validation calendar %s %r", url, pair)
        #     continue
        date = datetime.fromtimestamp(pair["date"])
        # note = f'Примечание: {pair["note"]}\n' if pair["note"] else ""
        # print(pair)
        # description = f"{pair['type']}\nПреподаватель: {pair['teachers_name']}\nГруппы: {pair['groups']}\n{note}"
        # if pair["url1"]:
        #     description += f"{pair['url1_description']}: {pair['url1']}\n"
        # if pair["url2"]:
        #     description += f"{pair['url2_description']}: {pair['url2']}\n"
        calendar.add_event(
            IEvent(
                summary=pair["name"],
                start=datetime(
                    date.year,
                    date.month,
                    date.day,
                    *map(int, pair["time_start"].split(":")),
                ),
                end=datetime(
                    date.year,
                    date.month,
                    date.day,
                    *map(int, pair["time_end"].split(":")),
                ),
                location=f"{pair['audience']}, {pair['location']}",
                description=pair["description"],
            )
        )

    return calendar.ical()


async def download_calendar_json(id: int, type: str):
    date_start, date_end = get_dates()
    async with ClientSession() as client:
        try:
            async with client.get(
                f"http://ruz.fa.ru/api/schedule/{type}/{id}?start={date_start}&finish={date_end}&lng=1",
                timeout=20,
            ) as request:
                pairs_list = await request.json(loads=loads)
                # if not pairs_list:
                #     raise EmptySchedule()
        except ClientError:
            raise ServiceUnavailable()
    pairs_list = PAIR_SCHEMA.load(pairs_list, many=True)
    print(pairs_list)
    return pairs_list
