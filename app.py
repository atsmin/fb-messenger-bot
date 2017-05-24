# -*- coding:utf-8 -*-
import os
import sys
import json
import redis

import requests
from flask import Flask, request

USERS = ('atsmin', 'erithin')
APIXU_URL = 'http://api.apixu.com/v1/forecast.json'

app = Flask(__name__)

r = redis.from_url(os.environ.get("REDIS_URL"))


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"].get("text")  # the message's text

                    send_message(sender_id, "わん")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


@app.route('/greet', methods=['POST'])
def greet():
    message = "え〜みなみくんまたきたの〜やだなぁ"
    sender_id = r.hget(USERS[0], 'sender_id')
    send_message(sender_id, message)
    return "ok", 200


@app.route('/countdown', methods=['GET'])
def countdown():
    from datetime import date, datetime, timedelta
    event = date(2017, 5, 28)  # FIXME
    today = (datetime.today() + timedelta(hours=9)).date()  # UTC to JST
    remain = (event - today).days

    message = ''
    if remain > 0:
        message = "熱海まであと{}日だよ。たのちみ！".format(remain)
    elif remain == 0:
        message = "熱海〜！！いいな〜！！"

    if message:
        for user in USERS:
            sender_id = r.hget(user, 'sender_id')
            send_message(sender_id, message)

    return "ok", 200


@app.route('/forecast', methods=['GET'])
def forecast():
    for user in USERS:
        message = '今日の{}の天気だよ！'.format(r.hget(user, 'city_jp'))
        sender_id = r.hget(user, 'sender_id')
        city = r.hget(user, 'city_en')
        forecast = get_forecast(city)
        text = forecast['text']
        if 'rain' in text or 'Rain' in text:
            message += '\n傘忘れないでね！'

        send_message(sender_id, message)
        send_attachment(sender_id, forecast['icon'])

    return "ok", 200


def get_forecast(city):
    response = requests.get(APIXU_URL, {
        'key': os.environ['APIXU_KEY'],
        'q': city,
        'days': 1
    })
    data = json.loads(response.text)
    condition = data['forecast']['forecastday'][0]['day']['condition']
    return condition


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_attachment(recipient_id, attachment):

    log("sending message to {recipient}: {attachment}".format(recipient=recipient_id, attachment=attachment))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": 'http:' + attachment
                }
            }
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
