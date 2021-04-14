import os

import requests
import slackweb
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
WEB_HOOK_LINKS = os.environ["SLACK_WEB_HOOKS_URL"]
BOT_OAUTH = os.environ["SLACK_BOT_OAUTH"]
POST_CHANEL_ID = os.environ["SLACK_POST_CHANEL_ID"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    #app.logger.info("test Request" + body)

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
        room_id = event.source.room_id
        return user_id, user_name, msg_type, room_id
    
    if event.source.type == "group":
        msg_type = "grouptalk"
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

    slack_info.notify(text=send_msg)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """
    Image Message
    """
    
    #get talk
    user_id, user_name, msg_type, room_id = get_event_info(event)

    #send lineImage recieve
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    img = message_content.content
    print('event', event)

    #slack
    send_msg = "[bot-line] {user_name}\n".format(user_name=user_name) \
        + "---\n" \
        + "{msg_type} ( {room_id} )\n".format(msg_type=msg_type, room_id=room_id) \
        + "送信者: {user_name} ( {user_id} )".format(user_name=user_name, user_id=user_id)

    file_name = "send_image_{message_id}".format(message_id=message_id)

    #send image
    url = 'https://slack.com/api/files.upload'
    files = {'file': img}
    param = {
        'token': BOT_OAUTH,
        'channels': POST_CHANEL_ID,
        'filename': file_name,
        'initial_comment': send_msg,
        'title': file_name
    }
    print("log", param)
    requests.post(url, params=param, files=files)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    