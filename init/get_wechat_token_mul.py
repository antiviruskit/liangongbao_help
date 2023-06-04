from init.get_wechat_secret import get_tok_uid


class GetWechatTokenMul:
    def main(self, user, passwd):
        memberId, token = get_tok_uid()
        user_info = {'memberId': memberId, 'token': token}
        with open('mul_token.txt', 'a', encoding='utf-8') as f:
            f.write(str(user_info) + '\n')
        if input("还继续扫描嘛？ q退出:").upper() == 'Q':
            raise SystemExit("程序退出")
