import sqlite3
import urllib3
import os
import json
import sys
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



class ChromeCookie:
    def __init__(self):
        self.domain = domain

    def dpapi_decrypt(self,encrypted):
        import ctypes
        import ctypes.wintypes
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [('cbData', ctypes.wintypes.DWORD),
                        ('pbData', ctypes.POINTER(ctypes.c_char))]
        p = ctypes.create_string_buffer(encrypted, len(encrypted))
        blobin = DATA_BLOB(ctypes.sizeof(p), p)
        blobout = DATA_BLOB()
        retval = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blobin), None, None, None, None, 0, ctypes.byref(blobout))
        if not retval:
            raise ctypes.WinError()
        result = ctypes.string_at(blobout.pbData, blobout.cbData)
        ctypes.windll.kernel32.LocalFree(blobout.pbData)
        return result

    def aes_decrypt(self,encrypted_txt):
        with open(os.path.join(os.environ['LOCALAPPDATA'],
                            r"Google\Chrome\User Data\Local State"), encoding='utf-8', mode="r") as f:
            jsn = json.loads(str(f.readline()))
        encoded_key = jsn["os_crypt"]["encrypted_key"]
        encrypted_key = base64.b64decode(encoded_key.encode())
        encrypted_key = encrypted_key[5:]
        key = self.dpapi_decrypt(encrypted_key)
        nonce = encrypted_txt[3:15]
        cipher = Cipher(algorithms.AES(key), None, backend=default_backend())
        cipher.mode = modes.GCM(nonce)
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_txt[15:])

    def chrome_decrypt(self,encrypted_txt):
        if sys.platform == 'win32':
            try:
                if encrypted_txt[:4] == b'x01x00x00x00':
                    decrypted_txt = self.dpapi_decrypt(encrypted_txt)
                    return decrypted_txt.decode()
                elif encrypted_txt[:3] == b'v10':
                    decrypted_txt = self.aes_decrypt(encrypted_txt)
                    return decrypted_txt[:-16].decode()
            except WindowsError:
                return None
        else:
            raise WindowsError

    def get_cookies_from_chrome(self,domain):
        sql = f'SELECT name, encrypted_value as value FROM cookies where host_key like "%{domain}%"'
        # chrome 96 版本以下
        # filename = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data\default\Cookies')
        # chrome96 版本以上
        filename = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data\default\Network\Cookies')
        con = sqlite3.connect(filename)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(sql)
        cookie = ''
        cookie_dict = {}
        for row in cur:
            # print("1111>>>>>",row)
            if row['value'] is not None:
                name = row['name']
                value = self.chrome_decrypt(row['value'])
                # print("2222>>>>",name,value)
                if value is not None:
                    cookie += name + '=' + value + ';'
                    cookie_dict[name] = value
        return cookie_dict



if __name__ == '__main__':
    domain = 'Google.com'   # 目标网站域名
    chromeCookie = ChromeCookie()
    cookie = chromeCookie.get_cookies_from_chrome(domain)
    print(cookie)





