# -*- coding=utf-8 -*-
import argparse
import sys
import traceback
import time
from config.LgbConfig import ACCOUNT


class Logger(object):
    def __init__(self, filename="Default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass

    def __getattr__(self, attr):
        return getattr(self.terminal, attr)


def parser_arguments():
    """
    参数解析
    :param argv:
    :return:
    """
    parser = argparse.ArgumentParser(description='链工宝让平凡的人懂得安全生产')
    parser.add_argument('-i', '--interface_call', action='store_true',
                        default=False, help='2023使用手机APP接口POST/GET运行')
    parser.add_argument('-v', '--visualization', action='store_true',
                        default=False, help='2022使用浏览器可视化运行')
    parser.add_argument('-a', '--adb_ocr', action='store_true',
                        default=False, help='2022使用ADB工具连接手机运行')
    parser.add_argument('-w', '--webpc', action='store_true',
                        default=False, help='2023使用Wechat登录网页版运行')
    parser.add_argument('-g', '--get_wechat_token_mul', action='store_true',
                        default=False, help='2023获取Wechat登录多个token')
    return parser


if __name__ == '__main__':
    parser = parser_arguments()
    args = parser.parse_args(sys.argv[1:])
    if args.interface_call:
        from init.interface_call import InterfaceCall
        app = InterfaceCall()
    elif args.visualization:
        from init.visualization import Visualization
        app = Visualization()
    elif args.adb_ocr:
        from init.adb_ocr import ADBOCR
        app = ADBOCR()
    elif args.webpc:
        from init.webpc import WEBPC
        app = WEBPC()
    elif args.get_wechat_token_mul:
        from init.get_wechat_token_mul import GetWechatTokenMul
        app = GetWechatTokenMul()
        ACCOUNT *= 100  # 需要录入的数量
    else:
        parser.print_help()
        sys.exit(0)

    sys.stdout = Logger('info.log')
    sys.stderr = sys.stdout
    print('+++++++++++++++++++++++++++++++++++++++++++++')
    print(time.strftime('%Y-%m-%d %H:%M:%S'))
    for ac in ACCOUNT:
        user = ac.get("USER") or ac.get("memberId")
        passwd = ac.get("PWD") or ac.get("token")
        print("开始答题: ", user, passwd)
        try:
            app.main(user, passwd)
        except SystemExit:
            exit(0)
        except:
            traceback.print_exc()
            if input("还继续嘛？ q退出:").upper() == 'Q':
                break
    print("程序运行结束！！！")
