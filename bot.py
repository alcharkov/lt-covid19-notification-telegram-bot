from datetime import date
from telegram.ext import Updater, CommandHandler, CallbackContext
import urllib.request
import json
import emoji

job_interval_in_seconds = 600
telegram_bot_token = ''
api_url = \
    'https://services.arcgis.com/XdDVrnFqA9CT3JgB/arcgis/rest/services/covid_statistics/FeatureServer/0/query?f=json&where=1%3D1&returnGeometry=false&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=Data%20desc&resultOffset=0&resultRecordCount=1&cacheHint=true'


class Covid19Model(object):
    def __init__(self, list):
        self.date = list['Data']
        self.cases = list['Atvejų_skaičius']
        self.cured = list['Pasveikimai']
        self.dead = list['Mirtys']


def get_results(last_date):
    processed_array = []

    with urllib.request.urlopen(api_url) as url:
        try:
            data = json.loads(url.read().decode())
            for x in data['features']:
                processed_array.append(x['attributes'])

        except (ValueError, KeyError, TypeError):
            print("JSON format error")
    if last_date != processed_array[0]['Data']:
        return processed_array


def watch(update, context):
    if 'job' in context.chat_data:
        context.chat_data['job']['instance'].enabled=True
        return
    context.chat_data['job'] = {'chat_id': update.message.chat_id, 'data': None}
    context.chat_data['job']['instance'] = context.job_queue.run_repeating(run_covid_api_check, interval=job_interval_in_seconds, first=0, context=context)
    update.message.reply_text('Covid-19 in Lithuania reminder set!')


def unwatch(update, context):
    if 'job' in context.chat_data:
        context.chat_data['job']['instance'].enabled=False
        #context.job_queue.stop()
        update.message.reply_text('Covid-19 in Lithuania reminder unset!')


def run_covid_api_check(context):
    if context.job.context.chat_data['job']['data'] is None:
        results = get_results(None)

        covid19Model = Covid19Model(results[0])
        context.job.context.chat_data['job']['data'] = covid19Model

        converted_date = date.fromtimestamp(covid19Model.date / 1000.0)
        message = "Date: {}\nCases: {}\nCured: {}\nDead: {}".format(converted_date, covid19Model.cases, covid19Model.cured,
                                                                covid19Model.dead)
        context.bot.send_message(chat_id=context.job.context.chat_data['job']['chat_id'], text=message)

    else:
        results = get_results(context.job.context.chat_data['job']['data'].date)

        if results is None:
            return

        covid19Model = Covid19Model(results[0])
        old_results = context.job.context.chat_data['job']['data']
        context.job.context.chat_data['job']['data'] = covid19Model

        converted_date = date.fromtimestamp(covid19Model.date / 1000.0)
        message = "Date: {}\n".format(converted_date)
        message += "Cases: {}\n".format(str(covid19Model.cases) + emoji.emojize(
            ':exclamation_mark:') if covid19Model.cases > old_results.cases else old_results.cases)
        message += "Cured: {}\n".format(str(covid19Model.cured) + emoji.emojize(
            ':exclamation_mark:') if covid19Model.cured > old_results.cured else covid19Model.cured)
        message += "Dead: {}".format(str(covid19Model.dead) + emoji.emojize(
            ':exclamation_mark:') if covid19Model.dead > old_results.dead else old_results.dead)

        context.bot.send_message(chat_id=context.job.context.chat_data['job']['chat_id'], text=message)

if __name__ == '__main__':
    updater = Updater(telegram_bot_token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('watch', watch, pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler('unwatch', unwatch, pass_job_queue=True, pass_chat_data=True))

    updater.start_polling()
    updater.idle()
