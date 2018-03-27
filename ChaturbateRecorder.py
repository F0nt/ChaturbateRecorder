import time, datetime, os, sys, requests, configparser, re, subprocess
from bs4 import BeautifulSoup
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    slash = "\\"
else:
    slash = "/"
from queue import Queue
from streamlink import Streamlink
from threading import Thread

Config = configparser.ConfigParser()
Config.read(sys.path[0] + "/config/config.conf")
save_directory = Config.get('paths', 'save_directory')
wishlist = Config.get('paths', 'wishlist')
interval = int(Config.get('settings', 'checkInterval'))
genders = re.sub(' ', '', Config.get('settings', 'genders')).split(",")
directory_structure = Config.get('paths', 'directory_structure').lower()
postProcessingCommand = Config.get('settings', 'postProcessingCommand')
username = Config.get("login", "username")
password = Config.get("login", "password")
try:
    postProcessingThreads = int(Config.get('settings', 'postProcessingThreads'))
except ValueError:
    pass
completed_directory = Config.get('paths', 'completed_directory').lower()

def now():
    return '[' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ']'

recording = []
wanted = []

def login():
    s.headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'referer': 'https://chaturbate.com/',
        'origin': 'https://chaturbate.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'content-type': 'application/x-www-form-urlencoded',
        }


    data = {'username': username, 'password': password, 'next': ''}
    result = s.get("https://chaturbate.com/")
    soup = BeautifulSoup(result.text, "html.parser")
    data['csrfmiddlewaretoken'] = soup.find('input', {'name': 'csrfmiddlewaretoken'}).get('value')

    result = s.post('https://chaturbate.com/auth/login/?next=/', data=data, cookies=result.cookies)
    if not checkLogin(result):
        print('Login failed. Check that your username and password is set correctly in the configuration file.')
        exit()
    else:
        print('Logged in successfully.')


def checkLogin(result):
    soup = BeautifulSoup(result.text, "html.parser")
    if soup.find('div', {'id': 'user_information'}) is not None:
        return True
    else:
        return False

def startRecording(model):
    global postProcessingCommand
    global processingQueue
    try:
        result = requests.get('https://chaturbate.com/api/chatvideocontext/{}/'.format(model)).json()
        session = Streamlink()
        session.set_option('http-headers', "referer=https://www.chaturbate.com/{}".format(model))
        streams = session.streams("hlsvariant://{}".format(result['hls_source'].rsplit('?')[0]))
        stream = streams["best"]
        fd = stream.open()
        now = datetime.datetime.now()
        filePath = directory_structure.format(path=save_directory, model=model, gender=result['broadcaster_gender'],
                                              seconds=now.strftime("%S"),
                                              minutes=now.strftime("%M"), hour=now.strftime("%H"),
                                              day=now.strftime("%d"),
                                              month=now.strftime("%m"), year=now.strftime("%Y"))
        directory = filePath.rsplit(slash, 1)[0]+slash
        if not os.path.exists(directory):
            os.makedirs(directory)
        if model in recording: return
        with open(filePath, 'wb') as f:
            recording.append(model)
            while model in wanted:
                try:
                    data = fd.read(1024)
                    f.write(data)
                except:
                    f.close()
                    break
        if postProcessingCommand:
            processingQueue.put({'model':model, 'path':filePath, 'gender':gender})
        elif completed_directory:
            finishedDir = completed_directory.format(path=save_directory, model=model,
                        gender=gender, seconds=now.strftime("%S"),
                        minutes=now.strftime("%M"),hour=now.strftime("%H"), day=now.strftime("%d"),
                        month=now.strftime("%m"), year=now.strftime("%Y"))

            if not os.path.exists(finishedDir):
                os.makedirs(finishedDir)
            os.rename(filePath, finishedDir+slash+filePath.rsplit[slash,1][0])
    except: 
        pass
    finally:
        if model in recording:
            recording.remove(model)
def postProcess():
    global processingQueue
    global postProcessingCommand
    while True:
        while processingQueue.empty():
            time.sleep(1)
        parameters = processingQueue.get()
        model = parameters['model']
        path = parameters['path']
        filename = path.rsplit(slash, 1)[1]
        gender = parameters['gender']
        directory = path.rsplit(slash, 1)[0]+slash
        subprocess.run(postProcessingCommand.split() + [path, filename, directory, model, gender])

def getOnlineModels():
    online = []
    global wanted
    s = requests.session()
    for gender in genders:
        try:
            data = {'categories': gender, 'num': 127}
            result = requests.post("https://roomlister.stream.highwebmedia.com/session/start/", data=data).json()
            length = len(result['rooms'])
            online.extend([m['username'].lower() for m in result['rooms']])
            data['key'] = result['key']
            while length == 127:
                result = requests.post("https://roomlister.stream.highwebmedia.com/session/next/", data=data).json()
                length = len(result['rooms'])
                data['key'] = result['key']
                online.extend([m['username'].lower() for m in result['rooms']])
        except:
            break
    f = open(wishlist, 'r')
    wanted =  list(set(f.readlines()))
    wanted = [m.strip('\n').split('chaturbate.com/')[-1].lower().strip().replace('/', '') for m in wanted]
    #wantedModels = list(set(wanted).intersection(online).difference(recording))
    '''new method for building list - testing issue #19 yet again'''
    wantedModels = [m for m in (list(set(wanted))) if m in online and m not in recording]
    for theModel in wantedModels:
            thread = Thread(target=startRecording, args=(theModel,))
            thread.start()
    f.close()


if __name__ == '__main__':
    s = requests.session()
    result = s.get('https://chaturbate.com/')
    if not checkLogin(result):
        login()
    AllowedGenders = ['female', 'male', 'trans', 'couple']
    for gender in genders:
        if gender.lower() not in AllowedGenders:
            print(gender, "is not an acceptable gender. Options are as follows: female, male, trans, and couple.")
            print("Please correct your config file.")
            exit()
    genders = [a.lower()[0] for a in genders]
    print()
    if postProcessingCommand != "":
        processingQueue = Queue()
        postprocessingWorkers = []
        for i in range(0, postProcessingThreads):
            t = Thread(target=postProcess)
            postprocessingWorkers.append(t)
            t.start()
    sys.stdout.write("\033[F")
    while True:
        sys.stdout.write("\033[K")
        print( now(),"{} model(s) are being recorded. Getting list of online models now".format(len(recording)))
        sys.stdout.write("\033[K")
        print("The following models are being recorded: {}".format(recording), end="\r")
        getOnlineModels()
        sys.stdout.write("\033[F")
        for i in range(interval, 0, -1):
            sys.stdout.write("\033[K")
            print(now(), "{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
            sys.stdout.write("\033[K")
            print("The following models are being recorded: {}".format(recording), end="\r")
            time.sleep(1)
            sys.stdout.write("\033[F")