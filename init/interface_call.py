import json
import time
import random

from config.url_conf import URLS
from utils.http_utils import HTTPClient
from LgbConfig import MIN_TIME, MAX_TIME
from utils.find_ansers import FindAnswers
from LgbConfig import CORRECT_ANSWER_NUM
from LgbConfig import ONLY_QUERYINFO, QUERYINFO_WRITE_FILE, QUERYINFO_WRITE_FILE_PATH
from LgbConfig import AUTO_LOTTERY


class InterfaceCall:
    def __init__(self) -> None:
        self.user = ""
        self.passwd = ""
        self.http_client = HTTPClient()
        self.find_answers = FindAnswers()
        self.answer_ques_num = 0
        self.result_dict = None

    def login(self):
        token_data = {"userName": self.user, "password": self.passwd}
        token_dict = self.http_client.send(URLS['login'], token_data)
        status = token_dict.get("status")
        if status == 20000:
            self.http_client.token = token_dict.get("data").get("token")
            self.http_client.memberId = token_dict.get("data").get("memberId")
            print("登录成功")
        else:
            print(token_dict)

    def start(self) -> bool:
        self.result_dict = self.http_client.send(URLS['competition'])
        if 'isAnswered' in self.result_dict.get('data'):
            print("每天只能挑战一次哦~")
            return False
        self.result_dict = self.http_client.send(URLS['start'], data={})
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
            print("<------恭喜您，满分！！！------>")
            return True
        return False

    def answer(self):
        while not self.judge_finish():
            quesid_, answer_ = self.get_correct_answer()
            data = {"quesId": "%s" % quesid_, "answerOptions": answer_}
            self.result_dict = self.http_client.send(
                URLS['answer'], data=json.dumps(data))
            self.answer_ques_num += 1  # 答题数+1
            time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def submit_competition(self):
        self.result_dict = self.http_client.send(URLS['submitcompetition'], data={})
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
                t_str = input("没有找到答案>>>>>>>>>>>>手动输入答案:").upper()
                if not t_str:
                    retry_flag = True
                for v in t_str:
                    if ord(v)-64 > len(answerOptions):
                        retry_flag = True
            return quesid_, self.find_answers.option2text(list(t_str), answerOptions)

    def query_account_rank(self):
        send_data = {'date': time.strftime('%Y-%m-%d')}
        self.result_dict = self.http_client.send(URLS['getrank'], data=send_data)
        data = self.result_dict.get('data')
        if not data:  # 无数据
            return
        query_list = ['area', 'dept']
        rank_str = ' '
        for v in query_list:
            v_tmp_list = data.get(v)
            for tmp in v_tmp_list:
                rank_str += tmp.get(v+'Name') + ':' + str(tmp.get('todayRank')) + '名'
                rank_str += ' '
        return rank_str

    def query_account_info(self):
        self.result_dict = self.http_client.send(URLS['competition'])
        data = self.result_dict.get('data')
        if not data:  # 无数据
            return
        memberName = '姓名:' + data.get('memberName')
        mobile = '手机号码:' + data.get('mobile')
        points = '我的积分:' + str(data.get('points'))
        userCategory = data.get('userCategory')
        if userCategory == 1:
            t_get_list = [item for item in ['thirdEnterpriseName', 'secondEnterpriseName', 'firstEnterpriseName'] if item in data]
            has_enterprise = '' if not t_get_list else t_get_list[0]
            EnterpriseName = '单位信息:' + data.get(has_enterprise, '')
        elif userCategory == 2:
            EnterpriseName = '单位信息:' + data.get('deptName', '')
        else:
            EnterpriseName = '单位信息:*'
        surplusNum = int(data.get('drawNum', None)) if data.get(
            'drawNum') is not None else -1
        self.result_dict = self.http_client.send(
            URLS['getdrawsurplusnum'], data={})
        surplusNum_retry = int(self.result_dict.get('data').get('surplusNum'))
        surplusNum = max(surplusNum, surplusNum_retry)
        surplusNum = '剩余抽奖次数:' + str(surplusNum)
        rank_str = self.query_account_rank()
        print(memberName, mobile, points, EnterpriseName, surplusNum, rank_str)
        if QUERYINFO_WRITE_FILE:
            with open(QUERYINFO_WRITE_FILE_PATH, 'a', encoding='utf-8') as f:
                t_str = ' '.join((memberName, mobile, points,
                                 EnterpriseName, surplusNum))
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
