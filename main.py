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
import time
import random
from threading import Thread
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
    "mongodb+srv://<user>:<password>@groupmagt.cgjzv3a.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())  # 要連結到的 connect string
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
    print(response)
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
        'lottery_switch': '1',
        'authentication_code': '',
        'lottery_item': '',
        'lottery_candidate': [],
        'lottery_win_count': ''
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
    else:
        return


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
    '10004': ['新竹縣'],
    '10005': ['苗栗縣', '苗栗'],
    '10007': ['彰化縣', '彰化'],
    '10008': ['南投縣', '南投'],
    '10009': ['雲林縣', '雲林'],
    '10020': ['嘉義市', '嘉義'],
    '10010': ['嘉義縣'],
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
        if "授權碼=" in message:
            code = message.split('=')[1]
            uname = line_bot_api.get_profile(uid).display_name
            res_txt = authenticated_check(gid, uname, code)
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=res_txt))

        elif '/help' == message:
            if group_enable(gid):
                weather_str = '💡[縣市]可輸入2~3個字之縣市名稱，提供全台22個行政縣市查詢\n範例輸入1:天氣=台北\n範例輸入2:天氣=新竹縣\nps.等號左右不需空白'
                zodiac_str = '💡[星座]可用1~3個字查詢12星座，\n範例輸入1:射\n範例輸入2:巨蟹\n範例輸入3：天蠍座'
                func_str = '💡[功能]可輸入：油價、匯率、星座、天氣、抽獎\n範例輸入1：油價 開\n範例輸入2：抽獎 關\nps.輸入完[功能]請空一格再輸入開或關!!!'
                auth_str = '💡[user]內可標記連續標記\n輸入範例1：新增管理員 @user1 @user2 @user3\n輸入範例2：刪除管理員 @user1 @user2\nps.輸入完新增(或刪除)管理員後，需空一格再開始標記'
                # lottery_v1 = '請依循步驟：\n1.🔐➛抽獎：此時機器人將請你輸入獎項\n2.🔐➛獎項=[您的獎項]：請連同”獎項=“一併輸入，等號左右不需空白\n3.🔐➛資格名單= [@user]：請連同“資格名單=”一併輸入，等號右側需空一格才能標記\n4.🔐➛開獎人數=[人數]：請連同“開獎人數=”一同輸入，等號左右不需空白\n5.結果將會在20秒後出爐\nps.輸入“抽獎”玩玩看就會囉，屆時機器人會一步步引導~'
                command = f'【指令集】\n===================\n\n➛：表示指令\n🔐：表示需要權限\n💡：表示額外說明\n\n—————查詢功能—————\n➛查油價：最新汽油柴油價目\n➛查匯率：最新NTD對外幣匯率\n➛天氣=[縣市]：近36hrs天氣預報\n➛[星座]：查詢本日星座運勢\n➛查管理員：列出群內所有管理員\n🔐➛查開關：查看各個功能是開啟或關閉\n\n{weather_str}\n\n{zodiac_str}\n\n—————設定功能—————\n🔐➛[功能] 開：打開指定功能\n🔐➛[功能] 關：關閉指定功能\n🔐➛新增管理員 [@user]：提升被標記成員的權限\n🔐➛刪除管理員 [@user]：移除被標記成員的權限\n\n{func_str}\n{auth_str}\n\n—————抽獎功能—————\n🔐➛抽獎範例：輸入後請直接複製範本並修改括號內容'

                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=command))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif "查油價" == message:
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
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif "查匯率" == message:
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
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        # 星座運勢
        elif message in [i for i in zodiacSigns_lst]:
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
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '天氣=' in message:
            if group_enable(gid):
                if switch_checker(gid, 'weather_switch'):
                    m = message.split('=')[1]
                    print(m)
                    city = [v[0] for k, v in cityId_dict.items()
                            if m in v]
                    print(city)
                    weather_res = weather(city[0])
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'{weather_res}'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=f'❌天氣預報功能未開啟'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        # 天氣預報
        # elif message in [i for i in cityId_lst]:
        #     if group_enable(gid):
        #         if switch_checker(gid, 'weather_switch'):
        #             city = [v[0] for k, v in cityId_dict.items()
        #                     if event.message.text in v]
        #             # key = [int(k) for k, v in cityId_dict.items() if event.message.text in v]
        #             weather_res = weather(city[0])
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text=f'{weather_res}'))
        #         else:
        #             line_bot_api.reply_message(event.reply_token, TextSendMessage(
        #                 text=f'❌天氣預報功能未開啟'))
        #     else:
        #         line_bot_api.reply_message(
        #             event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif "查管理員" == message:
            if group_enable(gid):
                managers_list = []
                group_managers_res = '—————本群管理員—————\n'
                managers_list = list_managers(gid)
                j = 0
                for i in managers_list:
                    j = j + 1
                    group_managers_res += f'➛{j}. {i}\n'
                group_managers_res += f'—————本群管理員—————\n總共{j}個人'
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'{group_managers_res}'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif " 開" in message or " 關" in message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    record = message.split(' ')[0]
                    open_close = message.split(' ')[1]
                    return_res = ''
                    if open_close == '開':
                        open_close = '1'
                    elif open_close == '關':
                        open_close = '0'
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
                    elif record == '抽獎':
                        return_res = switch_on_off(
                            gid, open_close, 'lottery_switch', record)
                    elif record == '入群歡迎圖':
                        return_res = switch_on_off(
                            gid, open_close, 'member_joined_figure_switch', record)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        text=return_res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '新增管理員' in message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    members = message.split(' @')[1:]
                    print(members)
                    managers_res = f'✨已成功將以下成員新增為管理員:\n'
                    if len(members) == 0:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text='⚠️指令不明確'))
                    else:
                        j = 0
                        for i in members:
                            j = j + 1
                            i.strip()
                            group_id_table.update_one(
                                {'_id': gid}, {"$push": {"group_managers": i.rstrip()}})
                            managers_res += f'{j}. {i.rstrip()}\n'
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=managers_res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '刪除管理員' in message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    members = message.split(' @')[1:]
                    print(members)
                    managers_res = f'✨已成功將以下成員從管理員刪除:\n'
                    if len(members) == 0:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text='⚠️指令不明確'))
                    else:
                        j = 0
                        for i in members:
                            j = j + 1
                            i.strip()
                            group_id_table.update_one(
                                {'_id': gid}, {'$pull': {'group_managers': i.rstrip()}})
                            # group_id_table.update_one(
                            #     {'_id': gid}, {"$push": {"group_managers": i.rstrip()}})
                            managers_res += f'{j}. {i.rstrip()}\n'
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=managers_res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '入群歡迎圖=' in message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    if switch_checker(gid, 'member_joined_figure_switch'):
                        welcome_figure = message.split('=')[1]
                        group_id_table.update_one({'_id': gid}, {
                            "$set": {"member_joined_figure": welcome_figure}})
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'🙌已成功設定入群歡迎圖'))
                    else:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'❌入群歡迎圖功能未開啟\n'))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '抽獎範例' == message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text='=== 抽獎 ===\n獎項\n{輸入獎項}\n\n資格名單\n{@user1 @user2}\n\n開獎人數\n{數量}'))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '=== 抽獎 ===' in message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    if switch_checker(gid, 'lottery_switch'):
                        # line_bot_api.reply_message(
                        #     event.reply_token, TextSendMessage(text=f'獎項=?'))
                        # push_thread = Thread(
                        #     target=lottery_push_message, args=(gid, 'item'))
                        # push_thread.start()
                        split_message = message.splitlines()
                        item = split_message[2]
                        print(item)
                        candidate_lst = split_message[5].split(' ')
                        print(candidate_lst)
                        win_count = split_message[8]
                        print(win_count)
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'🔥抽獎結果將在20秒後公布!\n🔥請耐心等候~~~~'))
                        lottery_thread = Thread(target=lottery, args=(
                            gid, item, candidate_lst, win_count))
                        lottery_thread.start()
                        lottery(gid, item, candidate_lst, win_count)
                    else:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=f'❌抽獎功能未開啟\n'))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))
        # elif '獎項=' in message:
        #     if group_enable(gid):
        #         if manager_check(gid, uid):
        #             if switch_checker(gid, 'lottery_switch'):
        #                 item = message.split('=')[1]
        #                 group_id_table.update_one(
        #                     {'_id': gid}, {"$set": {"lottery_item": item}})
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'資格名單=?'))
        #                 push_thread = Thread(
        #                     target=lottery_push_message, args=(gid, 'candidate'))
        #                 push_thread.start()
        #             else:
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'❌抽獎功能未開啟\n'))
        #         else:
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
        #     else:
        #         line_bot_api.reply_message(
        #             event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        # elif '資格名單=' in message:
        #     if group_enable(gid):
        #         if manager_check(gid, uid):
        #             if switch_checker(gid, 'lottery_switch'):
        #                 m = message.split('=')[1]
        #                 name_lst = m.split('@')[1:]
        #                 print(name_lst)
        #                 if len(name_lst) == 0:
        #                     line_bot_api.reply_message(
        #                         event.reply_token, TextSendMessage(text='⚠️指令不明確'))
        #                 else:
        #                     for i in name_lst:
        #                         i.strip()
        #                         group_id_table.update_one({'_id': gid}, {
        #                             "$push": {"lottery_candidate": i.rstrip()}})
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'開獎人數=?'))
        #                 push_thread = Thread(
        #                     target=lottery_push_message, args=(gid, 'count'))
        #                 push_thread.start()
        #             else:
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'❌抽獎功能未開啟\n'))
        #         else:
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
        #     else:
        #         line_bot_api.reply_message(
        #             event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        # elif '開獎人數=' in message:
        #     if group_enable(gid):
        #         if manager_check(gid, uid):
        #             if switch_checker(gid, 'lottery_switch'):
        #                 win_count = message.split('=')[1]
        #                 group_id_table.update_one(
        #                     {'_id': gid}, {"$set": {"lottery_win_count": win_count}})
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'🔥抽獎結果將在20秒後公布!\n🔥請耐心等候~~~~'))
        #                 lottery_res = group_id_table.find({'_id': gid})
        #                 lottery_item = ''
        #                 lottery_candidate = ''
        #                 lottery_win_count = ''
        #                 for i in lottery_res:
        #                     lottery_item = i['lottery_item']
        #                     lottery_candidate = i['lottery_candidate']
        #                     # lottery_win_count = i['lottery_win_count']
        #                 push_thread = Thread(
        #                     target=lottery, args=(gid, lottery_item, lottery_candidate, win_count))
        #                 push_thread.start()
        #             else:
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'❌抽獎功能未開啟\n'))
        #         else:
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
        #     else:
        #         line_bot_api.reply_message(
        #             event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        elif '查開關' == message:
            if group_enable(gid):
                if manager_check(gid, uid):
                    res = '【各功能目前狀態】\n\n'
                    res_lst = []
                    oc_res = group_id_table.find({'_id': gid})
                    for i in oc_res:
                        oil_ = '👌開啟中' if i['oil_switch'] == '1' else '❌關閉中'
                        exchange_ = '👌開啟中' if i['exchange_switch'] == '1' else '❌關閉中'
                        zodiac_ = '👌開啟中' if i['zodiacSigns_switch'] == '1' else '❌關閉中'
                        weather_ = '👌開啟中' if i['weather_switch'] == '1' else '❌關閉中'
                        lottery_ = '👌開啟中' if i['lottery_switch'] == '1' else '❌關閉中'
                        member_joined_figure_ = '👌開啟中' if i['member_joined_figure_switch'] == '1' else '❌關閉中'
                    res += f'➛查油價 {oil_}\n➛查匯率 {exchange_}\n➛星座運勢 {zodiac_}\n➛天氣預報 {weather_}\n➛抽獎功能 {lottery_}\n➛入群歡迎圖 {member_joined_figure_}'
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=res))
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))
        else:
            print('else detect!!!!!!!!!')

    except:
        print(Exception)


def lottery_push_message(gid, case):
    headers = {"content-type": "application/json; charset=UTF-8",
               'Authorization': 'Bearer {}'.format(access_token)}
    res = ''
    if case == 'item':
        res = f'請複製上列訊息並輸入獎項取代問號\n範例輸入如下⬇⬇⬇\n獎項=3000現金'
    elif case == 'candidate':
        res = f'請複製上列訊息並標記tag資格人以取代問號\n範例輸入如下⬇⬇⬇\n資格名單= @user1 @user2 @user3...'
    elif case == 'count':
        res = f'請複製上列訊息並輸入開獎人數取代問號\n範例輸入如下⬇⬇⬇\n開獎人數=1'
    else:
        res = f'⚠️指令不明確，請再輸入一次'

    body = {
        'to': gid,
        'messages': [{
            'type': 'text',
            'text': res
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',
                           headers=headers, data=json.dumps(body).encode('utf-8'))


def lottery(gid, item, candidate_lst, win_count):
    winner_lst = random.sample(candidate_lst, int(win_count))
    winner_str = ''
    for i in winner_lst:
        winner_str += f'@{i} '
    time.sleep(20)
    headers = {"content-type": "application/json; charset=UTF-8",
               'Authorization': 'Bearer {}'.format(access_token)}
    body = {
        'to': gid,
        'messages': [{
            'type': 'text',
            'text': f'🔥🔥抽獎結果出爐🔥🔥\n\n恭喜以下成員抽中 {item}\n\n{winner_str}'
        }]
    }

    # 向指定網址發送 request
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',
                           headers=headers, data=json.dumps(body).encode('utf-8'))
    print(req)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
