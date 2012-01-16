
import os, re, sys
import cookielib, urllib, urllib2
from cookielib import FileCookieJar
import xbmcgui, xbmcplugin, xbmcaddon
#sys.path.append( "/home/andi/workspace/xbmc-plugin-mindmadetools/lib");
from mindmade import *
from BeautifulSoup import BeautifulSoup

PLUGINID = "plugin.video.teleboy"

MODE_PLAY = "play"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_TITLE = "title"

URL_BASE = "http://www.teleboy.ch"
PLAYER = URL_BASE + "/tv/player/includes/flash/flashplayer_cinergy_v1_2_2.swf"
COOKIE_FILE = xbmc.translatePath( "special://home/addons/" + PLUGINID + "/resources/cookie.dat")
cookie = cookielib.LWPCookieJar( COOKIE_FILE)

pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon( id=PLUGINID)

def ensure_cookie():
    global cookie
    opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cookie))
    urllib2.install_opener( opener)
    try:
        cookie.revert( ignore_discard=True)
        return True
    except IOError:
        pass
    log( "logging in...")
    login = settings.getSetting( id="login")
    password = settings.getSetting( id="password")
    url = URL_BASE + "/layer/rectv/free_live_tv.inc.php"
    args = { "login": login,
             "password": password,
             "x": "13", "y": "17",
             "followup": "/tv/player/player.php" }
    
    reply = fetchHttp( url, args);
    
    if "Falsche Eingaben" in reply or "Login f&uuml;r Member" in reply:
        log( "login failure")
        notify( "Login Failure!", "Please set your login/password in the addon settings")
        xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=False)
        return False
    res = cookie.save( ignore_discard=True)
    log( "login ok")
    return True
        

def getUrl( url, args={}, hdrs={}):
    url = URL_BASE + url
    if ensure_cookie():
        html = fetchHttp( url, args, hdrs)
        if "Bitte melde dich neu an" in html:
            os.unlink( xbmc.translatePath( COOKIE_FILE));
            ensure_cookie()
            html = fetchHttp( url, args, hdrs)
    return html
        

def get_stationLogo( station):
    return URL_BASE + "/img/station/%d/logo_s_big1.gif" % int(station)

def get_streamparams( station):
    html = getUrl( "/tv/player/player.php?", { "station_id": station })
#    print html
    cid, cid2 = re.compile( "curChannel = '([0-9]*)'.*curDualChannel = '([0-9]*)'").findall( html)[0]
    if cid2 == "":
        cid2 = "0"
    
    hdrs = { "Referer": URL_BASE + "/tv/player/player.php" } 
    url = "/tv/player/includes/ajax.php"
    args = { "cmd": "getLiveChannelParams",
             "cid": cid, "cid2": cid2 }
    
    ans = getUrl( url, args, hdrs)
    ch, app, nello, a, b, c, d, e, dummy, version, x11 = ans.split( "|")[0:11] 

    ans = getUrl( "/tv/player/includes/getserver.php",
                  { "version": version, "nocache": "1314619521398" });
    ip = ans.split("=")[1]

    link = "rtmp://%s/%s" % (ip, x11)
    playpath = "%s%s.stream" % (cid, b)
    url = "%s playpath=%s swfurl=%s swfvfy=true live=true" % (link, playpath, PLAYER)
    for i in a,b,c,d,e:
        url = url + " conn=S:" + i
    return url

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

def addDirectoryItem( name, params={}, image="", total=0):
    '''Add a list item to the XBMC UI.'''
    img = "DefaultVideo.png"
    if image != "": img = image

    name = htmldecode( name)
    li = xbmcgui.ListItem( name, iconImage=img, thumbnailImage=image)
            
    li.setProperty( "Video", "true")
    
    params_encoded = dict()
    for k in params.keys():
        params_encoded[k] = params[k].encode( "utf-8")
    url = sys.argv[0] + '?' + urllib.urlencode( params_encoded)
    
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder = False, totalItems=total)
###########
# END TEMP
###########

def show_main():
    soup = BeautifulSoup( getUrl( "/tv/live_tv.php"))
    
    table = soup.find( "table", "listing")
    for tr in table.findAll( "tr"):
        td = tr.find( "td", attrs={"data-station-id": True})
        if td:
            id = int( td["data-station-id"])
            name = htmldecode( tr.find( "a", "mob24icon-black")["href"].split("/")[3])
            show = htmldecode( tr.find( "a").text)
            span = tr.find( "span", "show-description")
            desc = None
            if span:
                desc = span.text[5:]
            img = get_stationLogo( id)
            title = name + ": " + show
            if desc: label = title + " (+" + desc + ")"
            addDirectoryItem( label, { PARAMETER_KEY_STATION: str(id), PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_TITLE: title }, img)
#        print "%3d  %-10s %s (+%s)" % (id, name, show, desc)
    xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=True)


params = parameters_string_to_dict(sys.argv[2])
mode = params.get(PARAMETER_KEY_MODE, "0")
#    sys.exit()
    
# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_PLAY:

    station = params[PARAMETER_KEY_STATION]
    url = get_streamparams( station)
    img = get_stationLogo( station)

    li = xbmcgui.ListItem( params[PARAMETER_KEY_TITLE], iconImage=img, thumbnailImage=img)
    li.setProperty( "IsPlayable", "true")
    li.setProperty( "Video", "true")

    xbmc.Player().play( url, li)
