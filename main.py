import os

import requests, json
import slackweb
from flask import Flask, request, abort
from io import BytesIO
from PIL import Image, ImageOps
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageMessage, VideoMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
WEB_HOOK_LINKS = os.environ["SLACK_WEB_HOOKS_URL"]
BOT_OAUTH = os.environ["SLACK_BOT_OAUTH"]
POST_CHANNEL_ID = os.environ["SLACK_POST_CHANNEL_ID"]
USER_OAUTH = os.environ["SLACK_USER_OAUTH"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

#line
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    # app.logger("test Request" + body)
    print("!!! callback body !!!", body)

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

    print("!!! get eventtype !!!", event.source.type)

    #get username
    user_id = event.source.user_id
    try:
        user_name = line_bot_api.get_profile(user_id).display_name
    except LineBotApiError as e:
        user_name = "unknown"

    #get info talk
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

    if event.source.type == "image":
        msg_type = "image"
        room_id = None
        return user_id, user_name, msg_type, room_id

    if event.source.type == "video":
        msg_type = "video"
        room_id = None
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

    print("!!! get slack info !!!", slack_info)
    slack_info.notify(text=send_msg)

# image file
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
    img = message_content.content #画像データ
 
    #slack
    send_msg = "[bot-line] {user_name} 画像を送信．\n".format(user_name=user_name) \
               + "---\n" \
               + "送信元: {msg_type} ( {room_id} )\n".format(msg_type=msg_type, room_id=room_id) \
               + "送信者: {user_name} ( {user_id} )".format(user_name=user_name, user_id=user_id)

    file_name = "send_image_{message_id}".format(message_id=message_id)
    
    #send image
    url = 'https://slack.com/api/files.upload'
    headers = {"Authorization" : "Bearer "+ USER_OAUTH}
    files = {'file': img}
    param = {
        'user': user_id,
        'channels': POST_CHANNEL_ID,
        'filename': file_name,
        'initial_comment': send_msg,
        'title': file_name,
    }
    print("!!! send slack log !!!", param)
    res = requests.post(url, params=param, files=files, headers=headers)
    print("res", res.json())

# todo Video
@handler.add(MessageEvent, message=VideoMessage)
def handle_video_message(event):

    user_id, user_name, msg_type, room_id = get_event_info(event)

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    video = message_content.content
    print('!!! get video event !!!', event)

    send_msg = "[bot-line] {user_name} 動画を送信．\n".format(user_name=user_name) \
               + "---\n" \
               + "送信元: {msg_type} ( {room_id} )\n".format(msg_type=msg_type, room_id=room_id) \
               + "送信者: {user_name} ( {user_id} )".format(user_name=user_name, user_id=user_id)

    file_name = "send_video_{message_id}".format(message_id=message_id)

    url = 'https://slack.com/api/files.upload'
    headers = {"Authorization" : "Bearer "+ USER_OAUTH}
    files = {'file': video}
    param = {
        'user': user_id,
        # 'token': BOT_OAUTH,
        'channels': POST_CHANNEL_ID,
        'filename': file_name,
        'initial_comment': send_msg,
        'title': file_name,
    }
    print("!!! send slack video log !!!", param)
    res = requests.post(url, params=param, files=files, headers=headers)
    print("video res", res.json())


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    