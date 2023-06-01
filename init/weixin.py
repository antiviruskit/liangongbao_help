import copy
import json
import time
import random
from io import BytesIO
from PIL import Image
import qrcode
from pyzbar.pyzbar import decode
from utils.http_utils import HTTPClient
from utils.find_ansers import FindAnswers
from config.url_conf import URLS
from LgbConfig import CORRECT_ANSWER_NUM
from LgbConfig import ONLY_QUERYINFO, QUERYINFO_WRITE_FILE, QUERYINFO_WRITE_FILE_PATH
from LgbConfig import AUTO_LOTTERY
from LgbConfig import MIN_TIME, MAX_TIME


class WEIXIN:
    def __init__(self) -> None:
        self.http_client = HTTPClient()
        self.find_answers = FindAnswers()
        self.answer_ques_num = 0
        self.result_dict = None

    def login(self):
        res_text = self.http_client.send(URLS['wexin_request_qrcode'])
        assert isinstance(res_text, str), "错误：" + URLS['wexin_request_qrcode']
        key_str = '<img class="web_qrcode_img" src="/'
        idx = res_text.find(key_str)
        assert idx != -1, "没有找到微信提供的二维码图片"

        qrcode_href = res_text[idx:idx+70].split('"')[3]
        qrcode_uuid = qrcode_href.split('/')[-1]
        # print(qrcode_href, qrcode_uuid)

        qrcode_url = copy.deepcopy(URLS['wexin_request_uuid'])
        qrcode_url['req_url'] += qrcode_href

        res_content = self.http_client.send(qrcode_url)
        assert isinstance(res_text, str), "错误：" + qrcode_url
        image = Image.open(BytesIO(res_content))
        barcodes = decode(image)
        for barcode in barcodes:
            barcode_url = barcode.data.decode("utf-8")
        qr = qrcode.QRCode()
        barcode_url = URLS['wexin_confirm_request_uuid']['req_url'] + qrcode_uuid
        qr.add_data(barcode_url)
        qr.print_ascii(invert=True)
        
        scan_qrcode_sucess = False
        wexin_poll_confirm_request_uuid_url = copy.deepcopy(URLS['wexin_poll_confirm_request_uuid'])
        for _ in range(100):
            time.sleep(1)
            current_milli_time = lambda: str(int(round(time.time() * 1000)))
            wexin_poll_confirm_request_uuid_url['req_url'] += qrcode_uuid + '&_=' + current_milli_time()
            res_text = self.http_client.send(wexin_poll_confirm_request_uuid_url)
            if not isinstance(res_text, str): continue
            res = res_text.find('window.wx_errcode=405;window.wx_code=')
            if res == -1:
                continue
            else:
                print(res_text)

            scan_qrcode_sucess = True
            wx_code = res_text.split('=')[-1]
            wx_code = wx_code.replace('\'', '')
            wx_code = wx_code.replace(';', '')
            break
        assert scan_qrcode_sucess, "微信扫码超时,退出登录"

        get_log2023_uid_tok_url = copy.deepcopy(URLS['lgb2023_login'])
        get_log2023_uid_tok_url['req_url'] += wx_code + get_log2023_uid_tok_url['req_url_suffix']
        token_dict = self.http_client.send(get_log2023_uid_tok_url)
        status = token_dict.get("status")
        if status == 20000:
            self.http_client.token = token_dict.get("data").get("uidtok")
            self.http_client.memberId = token_dict.get("data").get("unionId")
            print("登录成功")
        else:
            print(token_dict)

    def start(self) -> bool:
        self.result_dict = self.http_client.send(URLS['lgb2023_competition'])
        if 'isAnswered' in self.result_dict.get('data'):
            print("每天只能挑战一次哦~")
            return False
        self.result_dict = self.http_client.send(URLS['lgb2023_start'], data={})
        msg = self.result_dict.get("result").get("msg")
        code = self.result_dict.get("result").get("code")
        if msg == "每天只能挑战一次哦~" and code == 9:
            print("每天只能挑战一次哦~")
            return False
        return True

    def judge_finish(self) -> bool:
        if self.answer_ques_num >= CORRECT_ANSWER_NUM:
            print("======已达设定最大答题数目,答题结束======")
            return True
        data = self.result_dict.get("data")
        if not data:
            print(self.result_dict)
            print("======服务器返回异常,账号答题结束======")
            return True
        ques = data.get("ques")
        if not ques:
            print("答题结束")
            return True
        return False

    def answer(self):
        while not self.judge_finish():
            quesid_, answer_ = self.get_correct_answer()
            data = {"quesId": "%s" % quesid_, "answerOptions": answer_}
            self.result_dict = self.http_client.send(
                URLS['lgb2023_answer'], data=json.dumps(data))
            self.answer_ques_num += 1  # 答题数+1
            time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def submit_competition(self):
        self.result_dict = self.http_client.send(URLS['lgb2023_submitcompetition'], data={})
        print('本次答对题目数：', self.result_dict.get('data').get("correctNum"))
        
    def get_correct_answer(self):
        quesid_ = ""
        answer_ = []

        if self.judge_finish():
            return quesid_, answer_

        ques = self.result_dict.get("data").get("ques")
        quesid_ = ques.get("quesId")
        quesTypeStr = ques.get("quesTypeStr")
        content = ques.get("content")
        answerOptions = ques.get("options")
        _, answer_ = self.find_answers.get_result(
            quesTypeStr, content, answerOptions)
        print("running:", str(self.answer_ques_num+1), quesTypeStr,
              content, answerOptions, answer_)
        if all([quesid_, answer_]):
            return quesid_, answer_
        else:
            retry_flag = True
            while retry_flag:
                retry_flag = False
                t_str = input("没有找到答案>>>>>>>>>>>>手动输入答案(abcd):").upper()
                if not t_str:
                    retry_flag = True
                for v in t_str:
                    if ord(v)-64 > len(answerOptions):
                        retry_flag = True
            return quesid_, self.find_answers.option2text(list(t_str), answerOptions)

    def task(self):
        self.login()
        if not ONLY_QUERYINFO and self.start():
            self.answer()
            self.submit_competition()
        self.http_client.del_cookies()
        self.http_client.rand_ua()
        time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def main(self, user, passwd):
        self.answer_ques_num = 0
        self.task()