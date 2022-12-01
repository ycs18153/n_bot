from hashlib import new
import imp
import os
from flask import Flask, request, abort, jsonify

import datetime

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

import re

import requests
import json
import pymongo
from pymongo import MongoClient
import certifi
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from general_func import authenticated_check, group_enable, switch_checker, list_managers, manager_check, switch_on_off, get_image_url
from crawler import oilPrice, exchangeRate, zodiacSigns, weather

app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi(
    '')
# Channel Secret
handler = WebhookHandler('')

access_token = ''
# 監聽所有來自 /callback 的 Post Request

mongoClient = pymongo.MongoClient(
    "mongodb+srv://<user>:<pass>@groupmagt.cgjzv3a.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())  # 要連結到的 connect string
groupMagt = mongoClient["groupMagt"]  # 指定資料庫
authenticaiton_code_table = groupMagt["authentication_code"]  # 指定資料表
group_id_table = groupMagt["group_id"]  # 指定資料表


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    json_body = request.get_json()
    print("Body info: ", json_body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("error occur here!!!! (In LineBot callback function)")
        abort(400)
    return 'OK'


@handler.add(LeaveEvent)
def bot_leave(event):
    gid = event.source.group_id
    group_id_table.update_one({'_id': gid}, {"$set": {"state": "0"}})


@handler.add(JoinEvent)
def bot_join(event):
    gid = event.source.group_id
    headers = {"content-type": "application/json; charset=UTF-8",
               'Authorization': 'Bearer {}'.format(access_token)}
    url = 'https://api.line.me/v2/bot/group/' + gid + '/summary'
    response = requests.get(url, headers=headers)
    response = response.json()
    group_id_table.insert_one({
        '_id': gid,
        'group_name': response['groupName'],
        'signup_date': str(datetime.date.today()),
        'exchange_switch': '1',
        'group_managers': [],
        'member_joined_figure': '',
        'member_joined_figure_switch': '0',
        'member_joined_word': '',
        'member_joined_word_switch': '0',
        'oil_switch': '1',
        'state': '0',
        'zodiacSigns_switch': '1',
        'weather_switch': '1',
        'authentication_code': ''
    })


@handler.add(MemberJoinedEvent)  # 入群歡迎圖
def welcome(event):
    # uid = event.joined.members[0].user_id
    gid = event.source.group_id
    image_url = ''
    if switch_checker(gid, 'member_joined_figure_switch'):
        image_url = get_image_url(gid)
    try:
        urls = image_url.rsplit('.', 1)[1]
        if urls == 'mp4':
            try:
                line_bot_api.reply_message(event.reply_token, VideoSendMessage(
                    original_content_url=image_url,  # 影片的網址，可以參考圖片的上傳方式
                    preview_image_url=image_url  # 影片預覽的圖片
                ))
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    text=f'❌當初上傳的圖片格式有誤，請重新上傳:\n入群歡迎圖=[圖檔網址]\n\nps.圖檔網址必須為https開頭，接受1MB以下圖檔(.jpg/.jpeg/.png/.gif)及10MB以下影片檔(./mp4)\n'))
        else:
            try:
                image_message = ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
                line_bot_api.reply_message(
                    event.reply_token, image_message)
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    text=f'❌當初上傳的圖片格式有誤，請重新上傳:\n入群歡迎圖=[圖檔網址]\n\nps.圖檔網址必須為https開頭，接受1MB以下圖檔(.jpg/.jpeg/.png/.gif)及10MB以下影片檔(./mp4)\n'))
    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=f'上傳的圖片格式有誤，請重新上傳:\n入群歡迎圖=[圖檔網址]\n\nps.圖檔網址必須為https開頭，接受1MB以下圖檔(.jpg/.jpeg/.png/.gif)及10MB以下影片檔(./mp4)\n'))


zodiacSigns_dict = {
    0: ["牡羊座", "牡羊", "牡"],
    1: ["金牛座", "金牛", "金"],
    2: ["雙子座", "雙子", "雙"],
    3: ["巨蟹座", "巨蟹", "巨"],
    4: ["獅子座", "獅子", "獅"],
    5: ["處女座", "處女", "處"],
    6: ["天秤座", "天秤", "天"],
    7: ["天蠍座", "天蠍"],
    8: ["射手座", "射手", "射"],
    9: ["摩羯座", "摩羯", "摩"],
    10: ["水瓶座", "水瓶", "水"],
    11: ["雙魚座", "雙魚"]
}
zodiacSigns_lst = [
    "牡羊座", "牡羊", "牡",
    "金牛座", "金牛", "金",
    "雙子座", "雙子", "雙",
    "巨蟹座", "巨蟹", "巨",
    "獅子座", "獅子", "獅",
    "處女座", "處女", "處",
    "天秤座", "天秤", "天",
    "天蠍座", "天蠍",
    "射手座", "射手", "射",
    "摩羯座", "摩羯", "摩",
    "水瓶座", "水瓶", "水",
    "雙魚座", "雙魚"
]

cityId_dict = {
    '63': ['臺北市', '台北市', '台北', '臺北'],
    '64': ['高雄市', '高雄'],
    '65': ['新北市', '新北'],
    '66': ['臺中市', '台中市', '台中', '臺中'],
    '67': ['臺南市', '台南市', '台南', '臺南'],
    '68': ['桃園市', '桃園'],
    '10018': ['新竹市', '新竹'],
    '10004': '新竹縣',
    '10005': ['苗栗縣', '苗栗'],
    '10007': ['彰化縣', '彰化'],
    '10008': ['南投縣', '南投'],
    '10009': ['雲林縣', '雲林'],
    '10020': ['嘉義市', '嘉義'],
    '10010': '嘉義縣',
    '10017': ['基隆市', '基隆'],
    '10013': ['屏東縣', '屏東'],
    '10002': ['宜蘭縣', '宜蘭'],
    '10015': ['花蓮縣', '花蓮'],
    '10014': ['臺東縣', '台東縣', '台東', '臺東'],
    '10016': ['澎湖縣', '澎湖'],
    '09020': ['金門縣', '金門'],
    '09007': ['連江縣', '連江']
}
cityId_lst = ['台北市', '臺北市', '台北', '臺北', '高雄市', '高雄', '新北市', '新北',
              '台中市', '臺中市', '台中', '臺中', '台南市', '臺南市', '台南', '臺南',
              '桃園市', '桃園', '新竹縣', '苗栗縣', '苗栗', '彰化縣', '彰化', '南投縣',
              '南投', '雲林縣', '雲林', '嘉義市', '嘉義', '嘉義縣', '基隆市', '基隆',
              '屏東縣', '屏東', '宜蘭縣', '宜蘭', '花蓮縣', '花蓮', '台東縣', '臺東縣',
              '台東', '臺東', '澎湖縣', '澎湖', '金門縣', '金門', '新竹市', '新竹']


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        gid = event.source.group_id
        uid = event.source.user_id
        message = event.message.text
        if "授權碼=" in event.message.text:
            code = message.split('=')[1]
            uname = line_bot_api.get_profile(uid).display_name
            res_txt = authenticated_check(gid, uname, code)
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=res_txt))

        elif "查油價" in event.message.text:
            if group_enable(gid):
                if switch_checker(gid, 'oil_switch'):
                    oil_res = oilPrice()
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'{oil_res}'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=f'❌查油價功能未開啟\n'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        elif "查匯率" in event.message.text:
            if group_enable(gid):
                if switch_checker(gid, 'exchange_switch'):
                    exchange_res = exchangeRate()
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'{exchange_res}'))
                    return '200'
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=f'❌查匯率功能未開啟'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        # 星座運勢
        elif event.message.text in [i for i in zodiacSigns_lst]:
            if group_enable(gid):
                if switch_checker(gid, 'zodiacSigns_switch'):
                    zodiacSigns_res = ''
                    key = [int(k) for k, v in zodiacSigns_dict.items()
                           if event.message.text in v]
                    zodiacSigns_res = zodiacSigns(int(key[0]))
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'{zodiacSigns_res}'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=f'❌星座運勢功能未開啟'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        # 天氣預報
        elif event.message.text in [i for i in cityId_lst]:
            if group_enable(gid):
                if switch_checker(gid, 'weather_switch'):
                    city = [v[0] for k, v in cityId_dict.items()
                            if event.message.text in v]
                    # key = [int(k) for k, v in cityId_dict.items() if event.message.text in v]
                    weather_res = weather(city[0])
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'{weather_res}'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=f'❌天氣預報功能未開啟'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        elif "查管理員" in event.message.text:
            if group_enable(gid):
                managers_list = []
                group_managers_res = '◢◢◢本群管理員◣◣◣\n'
                managers_list = list_managers(gid)
                j = 0
                for i in managers_list:
                    j = j + 1
                    group_managers_res += f'➛{j}. {i}\n'
                group_managers_res += f'總共{j}個人'
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'{group_managers_res}'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        elif " 開" in event.message.text or " 關" in event.message.text:
            if group_enable(gid):
                if manager_check(gid, uid):
                    record = message.split(' ')[0]
                    open_close = message.split(' ')[1]
                    return_res = ''
                    if open_close == '開':
                        open_close = '1'
                    elif open_close == '關':
                        open_close = '0'
                    else:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'指令不明確'))

                    if record == '油價':
                        return_res = switch_on_off(
                            gid, open_close, 'oil_switch', record)
                    elif record == '匯率':
                        return_res = switch_on_off(
                            gid, open_close, 'exchange_switch', record)
                    elif record == '星座':
                        return_res = switch_on_off(
                            gid, open_close, 'zodiacSigns_switch', record)
                    elif record == '天氣':
                        return_res = switch_on_off(
                            gid, open_close, 'weather_switch', record)
                    elif record == '入群歡迎圖':
                        return_res = switch_on_off(
                            gid, open_close, 'member_joined_figure_switch', record)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=return_res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼'))

        elif '新增管理員' in event.message.text:
            if group_enable(gid):
                if manager_check(gid, uid):
                    members = message.split(' @')[1:]
                    managers_res = f'✨已成功將以下成員新增為管理員:\n'
                    j = 0
                    for i in members:
                        j = j + 1
                        i.strip()
                        group_id_table.update_one({'_id': event.source.group_id}, {
                            "$push": {"group_managers": i.rstrip()}})
                        managers_res += f'{j}. {i.rstrip()}\n'
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=managers_res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼.'))

        elif '入群歡迎圖=' in event.message.text:
            if group_enable(event.source.group_id):
                if manager_check(event.source.group_id, event.source.user_id):
                    if switch_checker(gid, 'member_joined_figure'):
                        message = event.message.text
                        welcome_figure = message.split('=')[1]
                        group_id_table.update_one({'_id': event.source.group_id}, {
                            "$set": {"member_joined_figure": welcome_figure}})
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'🙌已成功設定入群歡迎圖'))
                    else:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'❌入群歡迎圖功能未開啟\n'))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'機器人尚未激活\n請先向官方取得授權碼.'))

        else:
            print('else detect!!!!!!!!!')

    except:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=f'⚠️機器人不支援服務個人或偵測到錯誤'))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
