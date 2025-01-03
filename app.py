from flask import Flask, request, send_from_directory, redirect
from flask_cors import CORS
from json import loads, dumps
from pathlib import Path
from hashlib import sha256
import werkzeug
import requests
import pymysql
import logging
import boto3
import time
import jwt
import os

db = None
s3chk = None
s3chkcache = False
SUBMIT_SERVER = "wheel-seminar.sparcs.net"

DOMAIN = None
AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None
AWS_S3_BUCKET_NAME = None
AWS_S3_CLOUDFRONT = None

app = Flask(__name__)
CORS(app)

logPath = Path('/var/log/sparcswheelclient.log')
logPath.touch()
logging.basicConfig(filename=logPath, level=logging.DEBUG)
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler(logPath))

tempPath = Path('tmp')
tempPath.mkdir(exist_ok=True)

# AWS LOGIN
aws = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def load_env():
    required = [
        "DOMAIN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_S3_BUCKET_NAME",
        "AWS_S3_CLOUDFRONT"
    ]

    for key in required:
        if key not in os.environ: raise EnvironmentError(f"{key} not found.")
        globals()[key] = os.environ.get(key)

def upload_to_s3(keyword: str, objname: str):
    if "/" in objname: raise ValueError("obj name error")
    uploadFile = tempPath / objname
    uploadFile.write_text(keyword)
    
    aws.upload_file(uploadFile, AWS_S3_BUCKET_NAME, objname)

    # return f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{objname}"
    return f"https://{AWS_S3_CLOUDFRONT}.cloudfront.net/{objname}"

def getinfo(sessid, typ = False):
    if typ:
        req = requests.get(f"https://{SUBMIT_SERVER}/sessinfo", headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'sessid': sessid, 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36', 'typ': 'd'})
    else:
        req = requests.get(f"https://{SUBMIT_SERVER}/sessinfo", headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'sessid': sessid, 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
    return req.json(), req.status_code

@app.route('/')
def send_index():
    return "<h1>IT WORKS! (API) [/ ]</h1>"

@app.route('/check')
def send_check():
    return "<h1>IT WORKS! (API) [/check]</h1>"

@app.route('/logout')
def send_logout(): 
    if "sessid" in request.headers:
        lgo = requests.post(f"https://{SUBMIT_SERVER}/logout", headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'sessid': request.headers["sessid"], 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
        if lgo.status_code == 200:
            global db
            if db is not None and db.open: db.close()
            db = None
        return lgo.text, lgo.status_code
    return dumps({'status': 'error', 'message': 'Invalid session'}), 400

@app.route('/auth/google', methods=['GET'])
def googleauth():
    if request.headers["Host"] != DOMAIN:
        if "localhost" in request.headers["Host"]:
            return dumps({'status': 'error', 'message': 'Invalid request. Check nginx config.'}), 400
        return dumps({'status': 'error', 'message': 'Invalid request, Wrong Host name!'}), 400
        
    senddata = {}
    senddata["domain"] = DOMAIN
    senddata["clienthash"] = sha256(Path(__file__).read_bytes()).hexdigest()
    
    req = requests.post(f"https://{SUBMIT_SERVER}/auth/request", json=senddata, headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
    if req.status_code == 200:
        return redirect(f"https://{SUBMIT_SERVER}/auth/google")
    return req.text, req.status_code

@app.route('/auth/callback', methods=['GET'])
def googleauthcallback():
    if request.headers["Host"] != DOMAIN:
        if "localhost" in request.headers["Host"]:
            return dumps({'status': 'error', 'message': 'Invalid request. Check nginx config.'}), 400
        return dumps({'status': 'error', 'message': 'Invalid request, Wrong Host name!'}), 400
    if "state" not in request.args: return "Invalid request", 400
    
    senddata = {}
    senddata["domain"] = DOMAIN
    senddata["state"] = request.args["state"]
    senddata["clienthash"] = sha256(Path(__file__).read_bytes()).hexdigest()
    senddata["bucket_name"] = AWS_S3_BUCKET_NAME
    senddata["bucket_cloudfront"] = AWS_S3_CLOUDFRONT

    rtn = requests.post(f"https://{SUBMIT_SERVER}/auth/last", json=senddata, headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
    if rtn.status_code != 200:
        return rtn.text, rtn.status_code
    
    global db
    if db is not None and db.open: db.close()
    db = None

    data = rtn.json()
    if "sessid" in data:
        return redirect(f"https://{DOMAIN}/callback.html?sessid={data['sessid']}")

# @app.route('/auth', methods=['POST'])
# def auth():
#     if "sessid" in request.headers:
#         _, status = getinfo(request.headers['sessid'])
#         if status == 200: return dumps({'status': 'success', 'sessid': request.headers['sessid']}), 200
#     if "userid" not in request.json or "userpw" not in request.json:
#         return dumps({'status': 'error', 'message': 'Invalid request, cannot find userid, pw'}), 400
    
#     if "Host" not in request.headers:
#         return dumps({'status': 'error', 'message': 'Invalid request, Wrong Host!'}), 400
    
#     if request.headers["Host"] != DOMAIN:
#         if "localhost" in request.headers["Host"]:
#             return dumps({'status': 'error', 'message': 'Invalid request. Check nginx config.'}), 400
#         return dumps({'status': 'error', 'message': 'Invalid request, Wrong Host name!'}), 400
    
#     if request.json["userid"] != DOMAIN.split(".")[0]:
#         return dumps({'status': 'error', 'message': 'Invalid request, Wrong userid with domain!'}), 400
    
#     senddata = dict(request.json)
#     senddata["clienthash"] = sha256(Path(__file__).read_bytes()).hexdigest()
#     senddata["bucket_name"] = AWS_S3_BUCKET_NAME
    
#     req = requests.post(f"https://{SUBMIT_SERVER}/auth", json=senddata, headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
#     if req.status_code == 200:
#         global db
#         if db is not None and db.open: db.close()
#         db = None
#     return req.text, req.status_code

@app.route('/sessinfo')
def checkseminar():
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    
    return getinfo(request.headers["sessid"])

@app.route('/dbconn', methods=['POST'])
def dbconn():
    # args
    # - host
    # - user
    # - password
    # - db
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    sessinfo, status = getinfo(request.headers["sessid"])
    if status != 200: return dumps({'status': 'error', 'message': 'Invalid session'}), 400
    if "host" not in request.json or "user" not in request.json or "password" not in request.json or "name" not in request.json:
        return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    
    global db
    try:
        db = pymysql.connect(host=request.json["host"], user=request.json["user"], password=request.json["password"], db=request.json["name"], charset="utf8")
        cur = db.cursor()

        cur.execute("""SHOW TABLES LIKE 'test'""")
        if cur.fetchone() is not None: cur.execute("""DROP TABLE test""")

        cur.execute("""
        CREATE TABLE test (
            userid VARCHAR(20) NOT NULL,
            typ VARCHAR(20) NOT NULL,
            keyword VARCHAR(2000) NOT NULL
        )
        """)
        cur.execute("""INSERT INTO test (userid, typ, keyword) VALUES (%s, %s, %s)""", (sessinfo[request.headers["sessid"]]['userid'], "prekeyword", requests.get(f"https://{SUBMIT_SERVER}/keyword", headers={'sessid': request.headers["sessid"], 'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'}).json()["keyword"]))
        return dumps({'status': 'success', 'message': 'Connected to database'}), 200
    except Exception as e:
        return dumps({'status': 'error', 'message': str(e)}), 500
    
@app.route('/dbstatus', methods=['GET'])
def dbstatus():
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    _, status = getinfo(request.headers["sessid"], True)
    if status != 200: return dumps({'status': 'error', 'message': 'Invalid session'}), 400
    global db
    if db is None: return dumps({'status': 'error', 'message': 'Database not connected'}), 503
    elif db.open is False: return dumps({'status': 'error', 'message': 'Database not connected'}), 503
    return dumps({'status': 'success', 'message': 'Database connected'}), 200


@app.route('/dbinsert', methods=['POST'])
def dbupload():
    if "sessid" not in request.headers or "code" not in request.json: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    sessinfo, status = getinfo(request.headers["sessid"])
    if status != 200: return dumps({'status': 'error', 'message': 'Invalid session'}), 400
    global db
    if db is None: return dumps({'status': 'error', 'message': 'Database not connected'}), 503
    elif db.open is False: return dumps({'status': 'error', 'message': 'Database not connected'}), 503

    try:
        cur = db.cursor()
        jwtkeys = requests.post(f"https://{SUBMIT_SERVER}/createjwt", headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'sessid': request.headers["sessid"], 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'}).json()
        tok = jwt.encode({"code": request.json["code"]}, jwtkeys["privkey"], algorithm="RS256")
        cur.execute("""INSERT INTO test (userid, typ, keyword) VALUES (%s, %s, %s)""", (sessinfo[request.headers["sessid"]]['userid'], "genkeyword", tok))
        db.commit()
        return dumps({'status': 'success', 'message': 'Inserted to database'}), 200
    except Exception as e:
        return dumps({'status': 'error', 'message': str(e)}), 500

@app.route('/s3run')
def s3run():
    global s3chk
    global s3chkcache
    s3chk = str(time.time())
    s3chkcache = False
    upload_to_s3(s3chk, "wheel-seminar-assignment-test.txt")
    url = f"https://{AWS_S3_CLOUDFRONT}.cloudfront.net/wheel-seminar-assignment-test.txt"

    if requests.get(url).text != s3chk: return dumps({'status': 'error', 'message': "Unexpected keyword. Check AWS Settings."}), 400
    return dumps({'status': 'success', 'message': 'S3 successfully working.'}), 200

@app.route('/s3status')
def s3status():
    global s3chk
    global s3chkcache
    if s3chk is None: return dumps({'status': 'error', 'message': 'S3 not checked'}), 400
    if s3chkcache: return dumps({'status': 'success', 'message': 'S3 successfully working.'}), 200
    
    # if requests.get(f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/wheel-seminar-assignment-test.txt").text != s3chk: return dumps({'status': 'error', 'message': "Unexpected keyword. Check AWS Settings."}), 400
    if requests.get(f"https://{AWS_S3_CLOUDFRONT}.cloudfront.net/wheel-seminar-assignment-test.txt").text != s3chk: return dumps({'status': 'error', 'message': "Unexpected keyword. Check AWS Settings."}), 400
    s3chkcache = True
    return dumps({'status': 'success', 'message': 'S3 successfully working.'}), 200

@app.route('/submit')
def submit():
    if "sessid" not in request.headers: return dumps({'status': 'error', 'message': 'Invalid request'}), 400
    sessinfo, status = getinfo(request.headers["sessid"])
    if status != 200: return dumps({'status': 'error', 'message': 'Invalid session'}), 400
    global db
    if db is None: return dumps({'status': 'error', 'message': 'Database not connected'}), 500
    elif db.open is False: return dumps({'status': 'error', 'message': 'Database not connected'}), 500

    # S3
    ups3token = requests.get(f"https://{SUBMIT_SERVER}/s3check", headers={'sessid': request.headers["sessid"], 'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty', 'clienthash': sha256(Path(__file__).read_bytes()).hexdigest(), 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
    if ups3token.status_code != 200: return ups3token.text, ups3token.status_code
    ups3token = ups3token.json()
    upload_to_s3(ups3token["token"], ups3token["objname"])

    cursor = db.cursor()

    senddata = {}
    try:
        senddata["sessid"] = request.headers["sessid"]
        cursor.execute("""SELECT keyword FROM test WHERE userid=%s AND typ=%s""", (sessinfo[request.headers["sessid"]]['userid'], "prekeyword"))
        senddata["prekeyword"] = cursor.fetchone()[0]
        cursor.execute("""SELECT keyword FROM test WHERE userid=%s AND typ=%s""", (sessinfo[request.headers["sessid"]]['userid'], "genkeyword"))
        senddata["genkeyword"] = cursor.fetchone()[0]
    except Exception as e:
        return dumps({'status': 'error', 'message': str(e)}), 500
    
    submit = requests.post(f"https://{SUBMIT_SERVER}/submit", json=senddata, headers={'Dnt': '1', 'Pragma': 'no-cache', 'Sec-Ch-Ua': 'Not.A/B', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'sessid': request.headers["sessid"], 'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors', 'clienthash': sha256(Path(__file__).read_bytes()).hexdigest(), 'Sec-Fetch-Dest': 'empty', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.1.0 Safari/537.36'})
    return submit.text, submit.status_code

if __name__ == '__main__':
    #sslPath = Path(__file__).parent / "ssl"
    #ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    #chainname = os.environ.get("CHAINNAME", "fullchain.pem")
    #keyname = os.environ.get("KEYNAME", "privkey.pem")
    #ssl_context.load_cert_chain(sslPath / chainname, sslPath / keyname)
    load_env()
    app.run(host='0.0.0.0', port=5000)