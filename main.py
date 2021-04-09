import os

import requests
import slackweb
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
WEB_HOOK_LINKS = os.environ["SLACK_WEB_HOOK_URL"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    # app.logger.info("test Request" + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK 200'

def get_event_info(event):
    """
    :param event: Line message
    :return: userID, username, sendtalk, roomID
    :rtype: str, str, str, str
    """

    user_id = event.source.user_id
    try:
        user_name = line_bot_api.get_profile(user_id).display_name
    except LineBotApiError as e:
        user_name = "unknown"

    if event.source.type == "user":
        msg_type = "personal"
        room_id = None
        return user_id, user_name, msg_type, room_id

    if event.source.type == "room":
        msg_type = "multitalk"
        room_id = event.source.group_id
        return user_id, user_name, msg_type, room_id

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """
    Text Message
    """

    slack_info = slackweb.Slack(url=WEB_HOOK_LINKS)

    user_id, user_name, msg_type, room_id = get_event_info(event)

    send_msg = "[bot-line] {user_name}\n".format(user_name=user_name) \
        + "{msg}\n".format(msg=event.message.text) \
        + "---\n" \

    slackweb.notify(text=send_msg)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    