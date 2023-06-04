import json
import time
import datetime
import random

from config.url_conf import URLS
from utils.http_utils import HTTPClient
from config.LgbConfig import MIN_TIME, MAX_TIME
from utils.find_ansers import FindAnswers
from config.LgbConfig import CORRECT_ANSWER_NUM
from config.LgbConfig import ONLY_QUERYINFO, QUERYINFO_WRITE_FILE, QUERYINFO_WRITE_FILE_PATH
from config.LgbConfig import AUTO_LOTTERY
from init.get_wechat_secret import get_tok_uid


class InterfaceCall:
    def __init__(self) -> None:
        self.user = ""
        self.passwd = ""
        self.http_client = HTTPClient()
        self.find_answers = FindAnswers()
        self.answer_ques_num = 0
        self.result_dict = None

    def login(self):
        self.result_dict = self.http_client.send(URLS['savelogin'])

        if self.login_save_valid():
            self.http_client.token = self.passwd
            self.http_client.memberId = self.user
            if self.login_check():
                return # 持久化登录成功
        self.http_client.memberId, self.http_client.token = get_tok_uid()

    def login_save_valid(self) -> bool:
        self.result_dict = self.http_client.send(URLS['savelogin'])
        if "SUCCESS" == self.result_dict.get('data'):
            return True
        return False

    def login_check(self) -> bool:
        URLS['login_check']['req_url'] = URLS['login_check']['req_url'].replace(
            'mytoken', self.http_client.token).replace('mymemberId', self.http_client.memberId)
        self.result_dict = self.http_client.send(URLS['login_check'])
        if "成功" == self.result_dict.get('message') and 20000 == self.result_dict.get('status'):
            print("使用token登录成功")
            return  True # 持久化登录成功
        return False

    def start(self) -> bool:
        self.result_dict = self.http_client.send(URLS['competition'])
        if 'isAnswered' in self.result_dict.get('data', {}):
            print("每天只能挑战一次哦~")
            return False
        self.result_dict = self.http_client.send(URLS['start'], data={})
        msg = self.result_dict.get("result", {}).get("msg")
        code = self.result_dict.get("result", {}).get("code")
        if msg == "您今日挑战已完成，明天再来挑战吧！" or code == 9:
            print("您今日挑战已完成，明天再来挑战吧！")
            return False
        return True

    def judge_finish(self) -> bool:
        if self.answer_ques_num >= CORRECT_ANSWER_NUM:
            print("======已达设定最大答题数目,答题结束======")
            return True
        data = self.result_dict.get("data")
        if data is None:
            print(self.result_dict)
            print("======服务器返回异常,账号答题结束======")
            return True
        ques = data.get("ques")
        if ques is None:
            print("答题结束")
            return True
        return False

    def answer(self):
        while not self.judge_finish():
            quesid_, answer_ = self.get_correct_answer()
            data = {"quesId": "%s" % quesid_, "answerOptions": answer_}
            self.result_dict = self.http_client.send(
                URLS['answer'], data=json.dumps(data))
            isRight = self.result_dict.get('data', {}).get('isRight')
            if isRight is None:
                print(self.result_dict)
            self.answer_ques_num += 1  # 答题数+1
            time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def submit_competition(self):
        self.result_dict = self.http_client.send(URLS['submitcompetition'], data={})
        print('本次答对题目数：', self.result_dict.get('data', {}).get("correctNum"))
        
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
                t_str = input("没有找到答案>>>>>>>>>>>>手动输入答案:").upper()
                if not t_str:
                    retry_flag = True
                for v in t_str:
                    if ord(v)-64 > len(answerOptions):
                        retry_flag = True
            return quesid_, self.find_answers.option2text(list(t_str), answerOptions)

    def query_account_rank(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        send_data = {'date': yesterday.strftime('%Y-%m-%d')}
        URLS['getrank']['req_url'] = URLS['getrank']['req_url'].replace('mydate', send_data.get('date'))
        self.result_dict = self.http_client.send(URLS['getrank'])
        data = self.result_dict.get('data')
        if data is None:  # 无数据
            return ''
        query_list = ['area', 'dept']
        rank_str = ' '
        for v in query_list:
            v_tmp_list = data.get(v, [])
            for tmp in v_tmp_list:
                rank_str += tmp.get(v+'Name') + ':' + str(tmp.get('todayRank')) + '名'
                rank_str += ' '
        return rank_str

    def query_account_info(self):
        self.result_dict = self.http_client.send(URLS['competition'])
        data = self.result_dict.get('data')
        if data is None:  # 无数据
            print(self.result_dict)
            print("======服务器返回异常======")
            return
        userCode = 'userCode:' + str(data.get('userCode'))
        points = '我的积分:' + str(data.get('points'))
        surplusNum = int(data.get('drawNum', None)) if data.get(
            'drawNum') is not None else -1
        self.result_dict = self.http_client.send(
            URLS['getdrawsurplusnum'], data={})
        surplusNum_retry = int(self.result_dict.get('data', {}).get('surplusNum', 0))
        surplusNum = min(surplusNum, surplusNum_retry)
        surplusNum = '剩余抽奖次数:' + str(surplusNum)
        rank_str = self.query_account_rank()
        print(userCode, self.http_client.token, self.http_client.memberId, points, surplusNum, rank_str)
        if QUERYINFO_WRITE_FILE:
            with open(QUERYINFO_WRITE_FILE_PATH, 'a', encoding='utf-8') as f:
                t_str = ' '.join((userCode, self.http_client.memberId, 
                                  self.http_client.token, points, surplusNum))
                f.write(t_str + rank_str + '\n')

    def auto_lottery(self):
        if not AUTO_LOTTERY:
            return
        self.result_dict = self.http_client.send(
            URLS['getdrawsurplusnum'], data={})
        surplusNum = int(self.result_dict.get('data').get('surplusNum'))
        if surplusNum == 0:
            print("您的抽奖次数已用完！")
        for i in range(surplusNum):
            self.result_dict = self.http_client.send(URLS['drawprize'], data={})
            data = self.result_dict.get('data')
            if not data:  # 无数据
                print("您的抽奖次数已用完！")
                return
            prizeName = data.get('prizeName')
            print('第%s次抽奖获得:' % (i+1), prizeName)
            time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def task(self):
        self.login()
        if not ONLY_QUERYINFO and self.start():
            self.answer()
            self.submit_competition()
        self.auto_lottery()
        self.query_account_info()
        self.http_client.del_cookies()
        self.http_client.rand_ua()
        time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def main(self, user, passwd):
        self.answer_ques_num = 0
        self.user = user
        self.passwd = passwd
        self.task()
