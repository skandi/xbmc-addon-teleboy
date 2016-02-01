
import os, re, sys, base64
import cookielib, urllib, urllib2
import xbmcgui, xbmcplugin, xbmcaddon
from mindmade import *
import simplejson

__author__     = "Andreas Wetzel"
__copyright__  = "Copyright 2011-2015, mindmade.org"
__credits__    = [ "Roman Haefeli", "Francois Marbot" ]
__maintainer__ = "Andreas Wetzel"
__email__      = "xbmc@mindmade.org"

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

MODE_RECORDINGS = "recordings"
MODE_PLAY = "play"
MODE_PLAY_RECORDING = "playrec"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_USERID = "userid"
PARAMETER_KEY_RECID  = "recid"

TB_URL = "http://www.teleboy.ch"
IMG_URL = "http://media.cinergy.ch"
API_URL = "http://tv.api.teleboy.ch"
API_KEY = base64.b64decode( "ZjBlN2JkZmI4MjJmYTg4YzBjN2ExM2Y3NTJhN2U4ZDVjMzc1N2ExM2Y3NTdhMTNmOWMwYzdhMTNmN2RmYjgyMg==")
COOKIE_FILE = xbmc.translatePath( "special://home/addons/" + PLUGINID + "/resources/cookie.dat")


pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon( id=PLUGINID)
cookies = cookielib.LWPCookieJar( COOKIE_FILE)

def ensure_login():
    global cookies
    opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener( opener)
    try:
        cookies.revert( ignore_discard=True)
        for c in cookies:
            if c.name == "cinergy_s":
                return True
    except IOError:
        pass
    cookies.clear()
    fetchHttp( TB_URL + "/watchlist")

    log( "logging in...")
    login = settings.getSetting( id="login")
    password = settings.getSetting( id="password")
    url = TB_URL + "/login_check"
    args = { "login": login,
             "password": password,
             "keep_login": "1" }

    reply = fetchHttp( url, args, post=True);

    if "Falsche Eingaben" in reply or "Anmeldung war nicht erfolgreich" in reply:
        log( "login failure")
        log( reply)
        notify( "Login Failure!", "Please set your login/password in the addon settings")
        xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=False)
        return False
    res = cookies.save( ignore_discard=True)

    log( "login ok")
    return True

def fetchHttpWithCookies( url, args={}, hdrs={}, post=False):
    if ensure_login():
        html = fetchHttp( url, args, hdrs, post)
        if "Bitte melde dich neu an" in html:
            os.unlink( xbmc.translatePath( COOKIE_FILE));
            if not ensure_login():
                return "";
            html = fetchHttp( url, args, hdrs, post)
        return html
    return ""

def get_stationLogoURL( station):
    return IMG_URL + "/t_station/" + station + "/icon320_dark.png"

def fetchApiJson( user_id, url, args={}):
    # get session key from cookie
    global cookies
    cookies.revert( ignore_discard=True)
    session_cookie = ""
    for c in cookies:
        if c.name == "cinergy_s":
            session_cookie = c.value
            break

    if (session_cookie == ""):
        notify( "Session cookie not found!", "Please set your login/password in the addon settings")
        return False

    hdrs = { "x-teleboy-apikey": API_KEY,
             "x-teleboy-session": session_cookie }
    url = API_URL + "/users/%s/" % user_id + url
    ans = fetchHttpWithCookies( url, args, hdrs)
    return simplejson.loads( ans)

def get_videoJson( user_id, sid):
    url = "stream/live/%s" % sid
    return fetchApiJson( user_id, url, {"alternative": "false"})

############
# TEMP
############
def parameters_string_to_dict( parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = urllib.unquote( paramSplits[1])
    return paramDict

def addDirectoryItem( name, params={}, image="", total=0, isFolder=False):
    '''Add a list item to the XBMC UI.'''
    img = "DefaultVideo.png"
    if image != "": img = image

    name = htmldecode( name)
    li = xbmcgui.ListItem( name, iconImage=img, thumbnailImage=image)

    if not isFolder:
	    li.setProperty( "Video", "true")

    params_encoded = dict()
    for k in params.keys():
        params_encoded[k] = params[k].encode( "utf-8")
    url = sys.argv[0] + '?' + urllib.urlencode( params_encoded)
    return xbmcplugin.addDirectoryItem(handle=pluginhandle, url=url, listitem=li, isFolder = isFolder, totalItems=total)
###########
# END TEMP
###########

def show_main():
    html = fetchHttpWithCookies( TB_URL + "/tv/live_tv.php")

    # extract user id
    user_id = ""
    lines = html.split( '\n')
    for line in lines:
        if "id: " in line:
            dummy, uid = line.split( ": ")
            user_id = uid[:-1]
            log( "user id: " + user_id)
            break;

    addDirectoryItem( "[ Recordings ]", { PARAMETER_KEY_MODE: MODE_RECORDINGS,
                                      PARAMETER_KEY_USERID: user_id},
                                      isFolder = True)

    content = fetchApiJson( user_id, "broadcasts/now", { "expand": "flags,station,previewImage", "stream": True })
    print( repr(content))
    for item in content["data"]["items"]:
        channel = item["station"]["name"]
        station_id = str(item["station"]["id"])
        title   = item["title"]
        tstart  = item["begin"][11:16]
        tend    = item["end"][11:16]
        label   = channel + ": " + title + " (" + tstart + "-" + tend +")"
        img     = get_stationLogoURL( station_id)
        addDirectoryItem( label, { PARAMETER_KEY_STATION: station_id, 
                          PARAMETER_KEY_MODE: MODE_PLAY, 
                          PARAMETER_KEY_USERID: user_id }, img)
    xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=True)


def show_recordings( user_id):
    content = fetchApiJson( user_id, "records/ready", { "limit": 500, "skip": 0})

    for item in content["data"]["items"]:
    	starttime = item["begin"].split("+")[0][:-3].replace( "T", " ")
    	label = starttime + " " + item["label"] + ": " + item["title"]
    	recid = str(item["id"])
    	addDirectoryItem( label, { PARAMETER_KEY_MODE: MODE_PLAY_RECORDING,
    							   PARAMETER_KEY_USERID: user_id,
    		                       PARAMETER_KEY_RECID: recid })

    xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=True)


def play_url( url, title, img=""):
    li = xbmcgui.ListItem( title, iconImage=img, thumbnailImage=img)
    li.setProperty( "IsPlayable", "true")
    li.setProperty( "Video", "true")

    xbmc.Player().play( url, li)


#
# xbmc entry point
############################################
sayHi()

params = parameters_string_to_dict(sys.argv[2])
mode = params.get(PARAMETER_KEY_MODE, "0")

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_RECORDINGS:
    user_id = params[PARAMETER_KEY_USERID]
    show_recordings( user_id)

elif mode == MODE_PLAY:
    user_id = params[PARAMETER_KEY_USERID]
    station = params[PARAMETER_KEY_STATION]
    json = get_videoJson( user_id, station)
    if not json:
        exit( 1)

    title = json["data"]["epg"]["current"]["title"]
    url = json["data"]["stream"]["url"]

    if not url: exit( 1)
    img = get_stationLogoURL( station)

    play_url( url, title, img)

elif mode == MODE_PLAY_RECORDING:
    user_id = params[PARAMETER_KEY_USERID]
    rec_id  = params[PARAMETER_KEY_RECID]

    url = "stream/record/%s" % rec_id
    json    = fetchApiJson( user_id, url)

    title = json["data"]["record"]["title"]
    url   = json["data"]["stream"]["url"]

    play_url( url, title)