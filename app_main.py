# coding:utf-8

import hashlib
import json
import re
import time

import requests
import xmltodict as xmltodict
from flask import Flask, request, abort
import logging

app = Flask(__name__)
# app.debug = True
logger = logging.getLogger(__name__)

# 设置 token
WECHAT_TOKEN = 'python'
# 图灵 apikey
TULING_APIKEY = 'd3b650fbd9c44f75bf93fff5050a6fee'

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/75.0.3770.80 Safari/537.36 "
}


class WeChat(object):
    def __init__(self):
        pass

    @staticmethod
    def get_verified(params=None):
        """
            验证 微信公众号
        :param params:
        :return:
        """
        timestamp = params.get("timestamp")
        nonce = params.get("nonce")
        # 对参数排序，拼接字符串
        temp_str = ''
        if timestamp and nonce and WECHAT_TOKEN:
            temp_str = [timestamp, nonce, WECHAT_TOKEN]
            temp_str.sort()
            temp_str = ''.join(temp_str)

        # 加密
        if temp_str:
            sign = hashlib.sha1(temp_str.encode("utf-8")).hexdigest()
            return sign

    @staticmethod
    def get_echo_text_message(input_xml_dict=None):
        """
            回传文本信息，如果不是文本信息，返回 特定字符串
        :param input_xml_dict:
        :return:
        """
        if input_xml_dict.get("MsgType") == 'text':
            res_xml_dict = {
                "ToUserName": input_xml_dict.get("FromUserName"),
                "FromUserName": input_xml_dict.get("ToUserName"),
                "CreateTime": int(time.time()),
                "MsgType": "text",
                "Content": input_xml_dict.get("Content")
            }
            logger.warning("recevie Content:{0}".format(input_xml_dict.get("Content")))
        else:  # 如果不是文本信息，返回 特定字符串
            res_xml_dict = {
                "ToUserName": input_xml_dict.get("FromUserName"),
                "FromUserName": input_xml_dict.get("ToUserName"),
                "CreateTime": int(time.time()),
                "MsgType": "text",
                "Content": "I LOVE U"
            }
        res_xml_str = xmltodict.unparse({'xml': res_xml_dict})
        return res_xml_str

    @staticmethod
    def is_english(data_str=None):
        if data_str:
            m = re.match(r'^[A-Za-z]+$', data_str)
            if m and m.group():
                return True

        return False

    @staticmethod
    def trans_by_api(query_data=None):

        # 百度翻译 英译中 api
        trans_by_api_url = "https://fanyi.baidu.com/v2transapi?from=en&to=zh"
        data = {
            "from": "en",
            "to": "zh",
            "query": str(query_data),
            "transtype": "translang"
        }
        res = requests.post(trans_by_api_url, headers=HEADERS, data=json.dumps(data))
        res_dict = json.loads(res.content.decode())
        if res_dict['errno'] == 0:
            res_data = res_dict["trans_result"]["data"][0]["dst"]

        else:
            logger.warning("errno: {0}".format(res_dict['errno']))
            res_data = "翻译出错"
        logger.warning(res_data)
        return res_data

    @staticmethod
    def res_text_message(input_xml_dict=None, send_content=None):
        if not (input_xml_dict and send_content):
            return ''

        res_xml_dict = {
            "ToUserName": input_xml_dict.get("FromUserName"),
            "FromUserName": input_xml_dict.get("ToUserName"),
            "CreateTime": int(time.time()),
            "MsgType": "text",
            "Content": str(send_content)
        }
        res_xml_str = xmltodict.unparse({'xml': res_xml_dict})
        return res_xml_str

    @staticmethod
    def res_by_tuling(input_xml_dict=None):
        tuling_api_url = "http://openapi.tuling123.com/openapi/api/v2"
        tuling_error_code = [5000, 6000, 4000, 4001, 4002, 4003, 4005, 4007, 4100, 4200, 4300, 4400, 4500, 4600, 4602,
                            7002, 8008, 0]

        if input_xml_dict.get("MsgType") != 'text':
            send_content = "哎呀，小鲸鱼只学会回复消息呢"
            return WeChat.res_text_message(input_xml_dict=input_xml_dict, send_content=send_content)

        tuling_request = dict()
        tuling_request["reqType"] = 0
        tuling_request["perception"] = {"inputText": {"text": input_xml_dict.get('Content')}}
        tuling_request["userInfo"] = {"apiKey": TULING_APIKEY, "userId": input_xml_dict.get('FromUserName')}
        # response = requests.post(tuling_api_url, json=json.dumps(tuling_request, ensure_ascii=False))
        response = requests.post(tuling_api_url, json=tuling_request)
        response_dict = json.loads(response.content.decode())
        logging.warning("response_dict: {}".format(response_dict))

        code = response_dict.get("intent").get("code")
        if code == 4003:
            # 该apikey没有可用请求次数
            send_content = "小鲸鱼有点累，不想聊天了"
        elif code in tuling_error_code:
            send_content = "小鲸鱼也不知道该怎么回复你了"
        else:
            # 返回码正常
            results = response_dict.get("results")[0]
            send_content = results.get("values").get("text")
        return WeChat.res_text_message(input_xml_dict=input_xml_dict, send_content=send_content)


@app.route('/wechat8000', methods=['POST', "GET"])
def wechat():
    # 获取参数
    params = request.args
    if not params:
        logger.warning("请求参数不存在")
        abort(403)
    sign = WeChat.get_verified(params=params)
    if sign != params.get("signature"):
        logger.warning("微信验证失败")
        abort(403)

    if request.method == "GET":
        echostr = params.get("echostr")
        if not echostr:
            logger.warning("请求参数 echostr 不存在")
            abort(400)
        return echostr

    elif request.method == "POST":
        xml_str = request.data
        if not xml_str:
            logger.warning("POST data 不存在")
            abort(400)
        logger.warning("POST data:{0}".format(xml_str))
        xml_dict = xmltodict.parse(xml_str)['xml']

        # 接收到文本信息
        if xml_dict.get("MsgType") == 'text':
            return WeChat.res_by_tuling(input_xml_dict=xml_dict)
        elif xml_dict.get("MsgType") == 'event':
            # 接收到事件
            if xml_dict.get("Event") == 'unsubscribe':
                # 取消关注
                return ''
            elif xml_dict.get("Event") == 'subscribe':
                # 关注
                send_content = "我是小鲸鱼，很高心认识你呀"
                return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'image':  # 图片
            send_content = "小鲸鱼还没学会看图呢"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'voice':  # 声音
            send_content = "声音"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'video':  # 视频
            send_content = "小鲸鱼还没学会看视频呢"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'shortvideo':  # 短视频
            send_content = "这个短视频小鲸鱼也不懂"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'location':  # 地理位置
            send_content = "这个位置小鲸鱼也没去过"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        elif xml_dict.get("MsgType") == 'link':  # 链接
            send_content = "小鲸鱼怕迷路，这个链接小鲸鱼不敢进去"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
        else:
            send_content = "这是什么鬼东西"
            return WeChat.res_text_message(input_xml_dict=xml_dict, send_content=send_content)
    else:
        logger.warning("请求方式错误")
        abort(403)


@app.route('/')
def index():
    return 'Hello World'


if __name__ == '__main__':
    app.run(port=5050, host="0.0.0.0")
