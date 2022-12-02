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

# from general_func import authenticated_check, group_enable, switch_checker, list_managers, manager_check, switch_on_off, get_image_url
# from crawler import oilPrice, exchangeRate, zodiacSigns, weather

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
                command = f'【指令集】\n===================\n\n➛：表示指令\n🔐：表示需要權限\n💡：表示額外說明\n\n—————查詢功能—————\n➛查油價：最新汽油柴油價目\n➛查匯率：最新NTD對外幣匯率\n➛天氣=[縣市]：近36hrs天氣預報\n➛[星座]：查詢本日星座運勢\n➛查管理員：列出群內所有管理員\n🔐➛查開關：查看各個功能是開啟或關閉\n\n{weather_str}\n\n{zodiac_str}\n\n—————設定功能—————\n🔐➛[功能] 開：打開指定功能\n🔐➛[功能] 關：關閉指定功能\n🔐➛新增管理員 [@user]：提升被標記成員的權限\n🔐➛刪除管理員 [@user]：移除被標記成員的權限\n\n{func_str}\n{auth_str}'

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
                    # elif record == '抽獎':
                    #     return_res = switch_on_off(
                    #         gid, open_close, 'lottery_switch', record)
                    # elif record == '入群歡迎圖':
                    #     return_res = switch_on_off(
                    #         gid, open_close, 'member_joined_figure_switch', record)
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

        # elif '抽獎範例' == message:
        #     if group_enable(gid):
        #         if manager_check(gid, uid):
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text='=== 抽獎 ===\n獎項\n{輸入獎項}\n\n資格名單\n{@user1 @user2}\n\n開獎人數\n{數量}'))
        #         else:
        #             line_bot_api.reply_message(
        #                 event.reply_token, TextSendMessage(text=f'⚠️沒有權限'))
        #     else:
        #         line_bot_api.reply_message(
        #             event.reply_token, TextSendMessage(text=f'❌機器人尚未激活\n請先向官方取得授權碼'))

        # elif '=== 抽獎 ===' in message:
        #     if group_enable(gid):
        #         if manager_check(gid, uid):
        #             if switch_checker(gid, 'lottery_switch'):
        #                 # line_bot_api.reply_message(
        #                 #     event.reply_token, TextSendMessage(text=f'獎項=?'))
        #                 # push_thread = Thread(
        #                 #     target=lottery_push_message, args=(gid, 'item'))
        #                 # push_thread.start()
        #                 split_message = message.splitlines()
        #                 item = split_message[2]
        #                 print(item)
        #                 candidate_lst = split_message[5].split(' ')
        #                 print(candidate_lst)
        #                 win_count = split_message[8]
        #                 print(win_count)
        #                 line_bot_api.reply_message(
        #                     event.reply_token, TextSendMessage(text=f'🔥抽獎結果將在20秒後公布!\n🔥請耐心等候~~~~'))
        #                 lottery_thread = Thread(target=lottery, args=(
        #                     gid, item, candidate_lst, win_count))
        #                 lottery_thread.start()
        #                 lottery(gid, item, candidate_lst, win_count)
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


def oilPrice():
    web = requests.get('https://gas.goodlife.tw/')
    soup = BeautifulSoup(web.content, "html.parser")

    web.close()

    cpc = soup.find_all('div', id='cpc')[0]  # 中油油價
    fpg = soup.find_all('div', id='cpc')[1]  # 台塑油價
    cpc_res = cpc.find_all('li')
    fpg_res = fpg.find_all('li')

    cpc_list = []
    fpg_list = []
    for i in cpc_res:
        if i:
            cpc_list.append(i.text.strip().replace('\n', '').split(':')[1])

    for j in fpg_res:
        if j:
            fpg_list.append(j.text.strip().replace('\n', '').split(':')[1])

    res_str = f'📅今日油價\n\n⛽今日中油油價\n92無鉛: {cpc_list[0]}元\n95無鉛: {cpc_list[1]}元\n98無鉛: {cpc_list[2]}元\n柴油: {cpc_list[3]}元\n\n⛽今日台塑油價\n92無鉛: {fpg_list[0]}元\n95無鉛: {fpg_list[1]}元\n98無鉛: {fpg_list[2]}元\n柴油: {fpg_list[3]}元'
    return res_str


def exchangeRate():
    web = requests.get('https://rate.bot.com.tw/xrt?Lang=zh-TW')
    soup = BeautifulSoup(web.content, "html.parser")

    web.close()

    rate = soup.find_all(
        'td', {'class': 'text-right display_none_print_show print_width'})

    # cash_rate[0, 1, 2, 7, 11, 14, 15, 18]
    # countries = ['USD', 'HKD', 'GBP', 'JPY', 'THB', 'EUR', 'KRW', 'CNY']

    lst = []
    for i in rate:
        if i:
            lst.append(i.text.strip())

    # lst = convert_1d_to_2d(lst, 4)

    lst = [lst[i:i + 4] for i in range(0, len(lst), 4)]

    matrix = []
    # len(lst) = 19
    for ele in range(len(lst)):
        if ele == 0 or ele == 1 or ele == 2 or ele == 7 or ele == 11 or ele == 14 or ele == 15 or ele == 18:
            matrix.append(lst[ele])

    res = f'💱最新匯率\n\n🇺🇸美金(USD)\n現金買入:{matrix[0][0]}\n現金賣出:{matrix[0][1]}\n即期買入:{matrix[0][2]}\n即期賣出:{matrix[0][3]}\n\n🇭🇰港幣(HKD)\n現金買入:{matrix[1][0]}\n現金賣出:{matrix[1][1]}\n即期買入:{matrix[1][2]}\n即期賣出:{matrix[1][3]}\n\n🇯🇵日元(JPY)\n現金買入:{matrix[3][0]}\n現金賣出:{matrix[3][1]}\n即期買入:{matrix[3][2]}\n即期賣出:{matrix[3][3]}\n\n🇹🇭泰銖(THB)\n現金買入:{matrix[4][0]}\n現金賣出:{matrix[4][1]}\n即期買入:{matrix[4][2]}\n即期賣出:{matrix[4][3]}\n\n🇪🇺歐元(EUR)\n現金買入:{matrix[5][0]}\n現金賣出:{matrix[5][1]}\n即期買入:{matrix[5][2]}\n即期賣出:{matrix[5][3]}\n\n🇰🇷韓元(KRW)\n現金買入:{matrix[6][0]}\n現金賣出:{matrix[6][1]}\n即期買入:{matrix[6][2]}\n即期賣出:{matrix[6][3]}\n\n🇨🇳人民幣(CNY)\n現金買入:{matrix[7][0]}\n現金賣出:{matrix[7][1]}\n即期買入:{matrix[7][2]}\n即期賣出:{matrix[7][3]}'
    return res


def zodiacSigns(key):
    today = datetime.date.today()
    d_sign = {
        0: '牡羊座', 1: '金牛座', 2: '雙子座', 3: '巨蟹座', 4: '獅子座', 5: '處女座', 6: '天秤座', 7: '天蠍座', 8: '射手座', 9: '摩羯座', 10: '水瓶座', 11: '雙魚座'
    }
    d_logo = {
        0: '♈', 1: '♉', 2: '♊', 3: '♋', 4: '♌', 5: '♍', 6: '♎', 7: '♏', 8: '♐', 9: '♑', 10: '♒', 11: '♓'
    }
    sign = ''
    logo = ''
    for k, val in d_sign.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
        if key == k:
            sign = val
    for k, val in d_logo.items():
        if key == k:
            logo = val

    web = requests.get(
        f'https://astro.click108.com.tw/daily_{key}.php?iAcDay={today}&iAstro={key}')

    soup = BeautifulSoup(web.content, "html.parser")

    # close requests
    web.close()

    today_lucky = soup.find('div', {'class': 'TODAY_LUCKY'})
    lucky_set = today_lucky.find_all('h4')

    lucky_lst = []
    for j in lucky_set:
        if j:
            lucky_lst.append(j.text.strip())

    today_word = soup.find('div', {'class': 'TODAY_WORD'})
    today_word = today_word.find('p')
    # print(today_word)
    today_total = soup.find('div', {'class': 'TODAY_CONTENT'})

    total_text = today_total.find_all('p')
    total_res = []
    for i in total_text:
        if i:
            total_res.append(i.text.strip())
    res = f'〖{today}〗\n{logo}{sign}星座運勢\n\n📝短評: {today_word.text.strip()}\n\n🔥今日{sign}完整解析\n\n🔢幸運數字: {lucky_lst[0]}\n🎨幸運顏色: {lucky_lst[1]}\n🌎開運方位: {lucky_lst[2]}\n🕰良辰吉時: {lucky_lst[3]}\n🍀幸運星座: {lucky_lst[4]}\n\n'
    for i in range(len(total_res)):
        res += f'{total_res[i]}\n'
    # res += f'{total_text.text.strip()}'
    return res


def weather(city):
    web = requests.get(
        f'https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=CWB-8F31035E-1873-4255-BF9C-44C035507136')
    web_json = web.json()
    web.close()
    locations = web_json['records']['location']

    # 3個array裡面的值都是以下順序：[天氣描述, 降雨機率, 最低溫, 舒適度, 最高溫]
    first_timming = []
    second_timming = []
    third_timming = []
    start_time0 = ''
    start_time1 = ''
    start_time2 = ''
    end_time0 = ''
    end_time1 = ''
    end_time2 = ''
    for i in locations:
        if city == i['locationName']:
            for j in i['weatherElement']:
                start_time0 = j['time'][0]['startTime'][5:-3]
                end_time0 = j['time'][0]['endTime'][5:-3]
                start_time1 = j['time'][1]['startTime'][5:-3]
                end_time1 = j['time'][1]['endTime'][5:-3]
                start_time2 = j['time'][2]['startTime'][5:-3]
                end_time2 = j['time'][2]['endTime'][5:-3]
                first_timming.append(
                    j['time'][0]['parameter']['parameterName'])
                second_timming.append(
                    j['time'][1]['parameter']['parameterName'])
                third_timming.append(
                    j['time'][2]['parameter']['parameterName'])

    res = f'〖{city} 36小時天氣預報〗\n\n[{start_time0}~{end_time0}]\n天氣現象: {first_timming[0]}\n降雨率: {first_timming[1]}%\n溫度: {first_timming[2]}°C~{first_timming[4]}°C\n舒適度: {first_timming[3]}\n\n[{start_time1}~{end_time1}]\n天氣現象: {second_timming[0]}\n降雨率: {second_timming[1]}%\n溫度: {second_timming[2]}°C~{second_timming[4]}°C\n舒適度: {second_timming[3]}\n\n[{start_time2}~{end_time2}]\n天氣現象: {third_timming[0]}\n降雨率: {third_timming[1]}%\n溫度: {third_timming[2]}°C~{third_timming[4]}°C\n舒適度: {third_timming[3]}'

    return res


def group_enable(group_id):
    res = group_id_table.find({'_id': group_id})
    for i in res:
        if i['state'] == '0':
            return False
        else:
            return True


def get_image_url(gid):
    figure_res = group_id_table.find({'_id': gid})
    print(figure_res)
    for i in figure_res:
        return i['member_joined_figure']


def switch_checker(gid, record):
    res = group_id_table.find({'_id': gid})
    for i in res:
        if i[record] == '1':
            return True
        else:
            return False


def switch_on_off(gid, open_close, key, record):
    if open_close == '0':
        group_id_table.update_one({'_id': gid}, {"$set": {key: open_close}})
        return f'😔{record} 功能已關閉'
    elif open_close == '1':
        group_id_table.update_one({'_id': gid}, {"$set": {key: open_close}})
        return f'🔥{record} 功能已開啟'
    else:
        return '指令不明確'


def manager_check(group_id, user_id):
    headers = {"content-type": "application/json; charset=UTF-8",
               'Authorization': 'Bearer {}'.format(access_token)}
    profile = requests.get('https://api.line.me/v2/bot/group/' +
                           group_id + "/member/" + user_id, headers=headers)
    profile = profile.json()
    user_name = profile['displayName']
    for i in group_id_table.find():
        if group_id == i['_id']:
            for j in i['group_managers']:
                if user_name == j:
                    return True
            return False


def list_managers(gid):
    managers = []
    manager_res = group_id_table.find({'_id': gid})
    for i in manager_res:
        return i['group_managers']
    #     for j in i['group_managers']:
    #         managers.append(j)
    # return managers


def authenticated_check(gid, uname, code):
    if group_enable(gid):
        return '⚠️此群組已註冊過'
    else:
        res = authenticaiton_code_table.find({'_id': code})
        for i in res:
            if i['enable'] == '0':
                # 更新授權碼狀態，避免重複使用
                authenticaiton_code_table.update_one(
                    {'_id': code}, {"$set": {"enable": "1"}})
                # 更新群組狀態，使群組成為已註冊用戶
                group_id_table.update_one({'_id': gid}, {
                    "$set": {"state": "1"}})
                # 將授權碼註冊在code欄位以便紀錄
                group_id_table.update_one({'_id': gid}, {
                    "$set": {"authentication_code": code}})
                # 將群組管理員
                group_id_table.update_one({'_id': gid}, {"$push": {
                    "group_managers": uname}})
                return f'🙌群組註冊成功!\n並已將{uname}設定為本群管理員'
        return '❌不正確或已註冊過的授權碼'


# def lottery(gid, item, candidate_lst, win_count):
#     winner_lst = random.sample(candidate_lst, int(win_count))
#     winner_str = ''
#     for i in winner_lst:
#         winner_str += f'{i} '
#     time.sleep(20)
#     headers = {"content-type": "application/json; charset=UTF-8",
#                'Authorization': 'Bearer {}'.format(access_token)}
#     body = {
#         'to': gid,
#         'messages': [{
#             'type': 'text',
#             'text': f'🔥🔥抽獎結果出爐🔥🔥\n\n恭喜以下成員抽中 {item}\n\n{winner_str}'
#         }]
#     }

#     # 向指定網址發送 request
#     req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',
#                            headers=headers, data=json.dumps(body).encode('utf-8'))
#     print(req)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
