import requests
import json
import io
import random
import time
import re
import pyDes
import base64
import uuid
import sys
import getopt

from pwd_headers import pwdEncrypt,htmlParser

class DailyCP:
    def __init__(self, host="sise"):
        self.key = "ST83=@XV"#dynamic when app update
        self.t = str(int(round(time.time() * 1000)))
        self.session = requests.session()
        self.host = host + ".campusphere.net"
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0",
            "X-Requested-With": "XMLHttpRequest",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            # "User-Agent": "okhttp/3.12.4"
        })
        url = "https://{host}/iap/login?service=https://{host}/portal/login".format(host=self.host)
        ret = self.session.get(url).url
        self.client = ret[ret.find("=")+1:]
        self.session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
        url = "https://{host}/iap/security/lt".format(host=self.host)
        ret = json.loads(self.session.post(url,data="lt={client}".format(client=self.client)).text)
        self.client = ret["result"]["_lt"]
        self.encryptSalt = ret["result"]["_encryptSalt"]

    def encrypt(self,text):
        k = pyDes.des(self.key, pyDes.CBC, b"\x01\x02\x03\x04\x05\x06\x07\x08", pad=None, padmode=pyDes.PAD_PKCS5)
        ret = k.encrypt(text)
        return base64.b64encode(ret).decode()

    def decrypt(self,text):
        k = pyDes.des(self.key, pyDes.CBC, b"\x01\x02\x03\x04\x05\x06\x07\x08", pad=None, padmode=pyDes.PAD_PKCS5)
        ret = k.decrypt(base64.b64decode(text))
        return ret.decode()

    def checkNeedCaptcha(self, username):
        url = "https://{host}/iap/checkNeedCaptcha?username={username}&_=".format(host=self.host,username=username)
        ret = self.session.get(url)
        ret = json.loads(ret.text)
        return ret["needCaptcha"]

    def generateCaptcha(self):
        url = "https://{host}/iap/generateCaptcha?ltId={client}&codeType=2&".format(host=self.host,client=self.client)
        ret = self.session.get(url)
        return ret.content

    def getBasicInfo(self):
        url = "https://{host}/iap/tenant/basicInfo".format(host=self.host)
        ret = self.session.post(url,data="{}").text
        return json.loads(ret)

    def login(self, username, password, captcha=""):
        url = "http://ids.vpn.jlenu.edu.cn/authserver/login?service=https%3A%2F%2Fjltiet.campusphere.net%2Fportal%2Flogin"
        html = self.session.get(url).content.decode('utf8')
        key, data = htmlParser(html)
        self.username = username
        body = {
            "username": username,
            "password": pwdEncrypt(password,key),
            "lt": self.client,
            "captcha": captcha,
            "rememberMe": "true",
            "dllt": "",
            "mobile": ""
        }
        body.update(data)
        self.session.headers["Content-Type"] = "application/x-www-form-urlencoded"
        text = self.session.post(url, data=body)
        if text.url == 'https://jltiet.campusphere.net/portal/index.html':
            return True
        else: return False

    def getCollectorList(self):
        body = {
            "pageSize": 10,
            "pageNumber": 1
        }
        self.session.headers["Content-Type"] = "application/json"
        url = "https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList".format(host=self.host)
        ret = self.session.post(url, data=json.dumps(body))
        ret = json.loads(ret.text)
        return ret["datas"]["rows"]

    def getNoticeList(self):
        body = {
            "pageSize": 10,
            "pageNumber": 1
        }
        self.session.headers["Content-Type"] = "application/json"
        url = "https://{host}/wec-counselor-stu-apps/stu/notice/queryProcessingNoticeList".format(host=self.host)
        ret = self.session.post(url, data=json.dumps(body))
        ret = json.loads(ret.text)
        return ret["datas"]["rows"]

    def confirmNotice(self, wid):
        body = {
            "wid": wid
        }
        self.session.headers["Content-Type"] = "application/json"
        url = "https://{host}/wec-counselor-stu-apps/stu/notice/confirmNotice".format(host=self.host)
        ret = self.session.post(url, data=json.dumps(body))
        ret = json.loads(ret.text)
        if ret["message"] == "SUCCESS":return True
        else:
            print(ret["message"])
            return False

    def getCollectorDetail(self, collectorWid):
        url = "https://{host}/wec-counselor-collector-apps/stu/collector/detailCollector".format(host=self.host)
        body = {
            "collectorWid": collectorWid
        }
        self.session.headers["Content-Type"] = "application/json"
        ret = self.session.post(url, data=json.dumps(body))
        ret = json.loads(ret.text)["datas"]
        url = ret["form"]["formContent"]
        return ret

    def getCollectorFormFiled(self, formWid, collectorWid):
        url = "https://{host}/wec-counselor-collector-apps/stu/collector/getFormFields".format(host=self.host)
        body = {
            "pageSize": 50,
            "pageNumber": 1,
            "formWid": formWid,
            "collectorWid": collectorWid
        }
        self.session.headers["Content-Type"] = "application/json"
        ret = self.session.post(url, data=json.dumps(body))
        ret = json.loads(ret.text)["datas"]["rows"]
        return ret

    def submitCollectorForm(self, formWid, collectWid, schoolTaskWid, rows, address):
        url = "https://{host}/wec-counselor-collector-apps/stu/collector/submitForm".format(host=self.host)
        body = {
            "formWid": formWid,
            "collectWid": collectWid,
            "schoolTaskWid": schoolTaskWid,
            "form": rows,
            "address": address
        }
        self.session.headers["Content-Type"] = "application/json"
        # self.session.headers["extension"] = "1" extension
        extension = {"deviceId":str(uuid.uuid4()),"systemName":"未来操作系统","userId":self.username,"appVersion":"8.1.13","model":"红星一号量子计算机","lon":0.0,"systemVersion":"初号机","lat":0.0}
        self.session.headers.update({"Cpdaily-Extension": self.encrypt(json.dumps(extension))})
        ret = self.session.post(url, data=json.dumps(body))
        print(ret.text)
        ret = json.loads(ret.text)
        if ret["message"] == "SUCCESS":return True
        else:
            print(ret["message"])
            return False

    def autoFill(self, rows):
        # isRequired
        for item in rows:
            index = 0
            while index < len(item["fieldItems"]):
                if item["fieldItems"][index]["isSelected"] == 1:index = index + 1
                else:item["fieldItems"].pop(index)

    def autoComplete(self, address):
        collectList = self.getCollectorList()
        print(collectList)
        for item in collectList:
            detail = self.getCollectorDetail(item["wid"])
            form = self.getCollectorFormFiled(
                detail["collector"]["formWid"], detail["collector"]["wid"])
            self.autoFill(form)
            # you can edit this form content by your self.
            # autoFill can fill the form with default value.
            self.submitCollectorForm(detail["collector"]["formWid"], detail["collector"]
                            ["wid"], detail["collector"]["schoolTaskWid"], form, address)

        confirmList = self.getNoticeList()
        print(confirmList)
        for item in confirmList:
            self.confirmNotice(item["noticeWid"])

def main(argv):
    '''try:
        opts, args = getopt.getopt(argv, "h", [])
        for opt, arg in opts:
            if opt == '-h':
                print("useage:\nDailyCP.py <school> <account> <password> <location>\n\n<school>: the address prefix of your school, if the address of your school is \"sise.campusphere.net\", then you can input sise.\n<account>: the login account of your school, usually is your student number.\n<password>: your login password.\n<location>: e.g.:中国广东省佛山市禅城区福贤路X号")
                sys.exit()
        if len(args) != 4:
            print('useage: DailyCP.py <school> <account> <password> <location>')
            sys.exit()
    except getopt.GetoptError:
        print('useage: DailyCP.py <school> <account> <password> <location>')
        sys.exit()
    else:
        school = str(args[0])
        account = str(args[1])
        password = str(args[2])
        address = str(args[3])'''
    school = 'jltiet'   #不要动
    account = ''       #工师id
    password = ''       #密码
    address = '中国'        #地理位置
    app = DailyCP(school)
    flag = 0
    while True:
        
        ret = app.login(account, password)
        time.sleep(3)
        if ret:
            print("Login succeeded.")
            break
        else:
            flag = flag + 1
            print("Login failed. Number of login attempts:" + str(flag))
        if flag >= 10:
            print("Can't login, exit.")
            sys.exit()
    app.autoComplete(address)

if __name__ == "__main__":
    main(sys.argv[1:])

#鸣谢:谷玉阳,Socular
#由:https://github.com/LemoFire/DailyCP 改编而成
#版本v1.0
#功能：自动签到


