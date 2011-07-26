
import os, re, sys
import cookielib, urllib, urllib2
from cookielib import FileCookieJar
import xbmcgui, xbmcplugin, xbmcaddon
#sys.path.append( "/home/andi/workspace/xbmc-plugin-mindmadetools/lib");
from mindmade import htmldecode, fetchHttp, notify
from BeautifulSoup import BeautifulSoup

CHANNELS = {
    "1": "111.stream",
    "2": "101.stream",
    "3": "11.stream",
    "4": "81.stream",
    "5": "241.stream",
    "6": "91.stream",
    "7": "291.stream",
    "8": "51.stream",
    "10": "71.stream",
    "11": "141.stream",
    "23": "321.stream",
    "24": "1611.stream",
    "25": "131.stream",
    "26": "311.stream",
    "28": "521.stream",
    "30": "301.stream",
    "31": "511.stream",
    "33": "351.stream",
    "35": "391.stream",
    "36": "331.stream",
    "72": "1971.stream",
    "138": "1701.stream",
    "154": "151.stream",
    "162": "61.stream",
    "279": "5011.stream",
    "sf1_o": "1591.stream",
    "arte_o": "201.stream",
    "sf2_o": "1081.stream",
    "zdfneo": "121.stream",
    "atv": "211.stream",
    "ntv": "401.stream",
    "euronews": "2161.stream",
    "phoenix": "531.stream",
    "swr": "541.stream",
    "dasvierte": "1721.stream",
    "nickelodeon": "221.stream",
    "deluxe": "1921.stream",
    "viva": "171.stream",
    "cnn": "411.stream",
    "bbc1": "691.stream",
    "bbc2": "1891.stream",
    "bbcworld": "431.stream",
    "cnbc": "461.stream",
    "itv1": "701.stream",
    "itv2": "711.stream",
    "aljazeera": "2151.stream",
}

REMOTE_DBG = False 

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)

PLUGINID = "plugin.video.teleboy"

MODE_PLAY = "play"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_TITLE = "title"

URL_BASE = "http://www.teleboy.ch"
PLAYER = URL_BASE + "/tv/player/includes/flash/flashplayer_cinergy_v1_1_6.swf"
COOKIE_FILE = os.path.join( os.getcwd(), "resources", "cookie.dat")
cookie = cookielib.LWPCookieJar()

pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon( id=PLUGINID)

def ensure_cookie():
    global cookie
    opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cookie))
    urllib2.install_opener( opener)
#    try:
#        cookie.load( COOKIE_FILE)
#    except IOError:
    login = settings.getSetting( id="login")
    password = settings.getSetting( id="password")
    url = URL_BASE + "/layer/rectv/free_live_tv.inc.php"
    args = { "login": login, "password": password, "x": "13", "y": "17", "followup": "/tv/player/player.php" }
    hdrs = { "User-Agent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.17) Gecko/20110422 Ubuntu/10.04 (lucid) Firefox/3.6.17" }
    req = urllib2.Request( url, urllib.urlencode( args), hdrs)
    r = urllib2.urlopen( req)
    reply = r.read()
    if "Falsche Eingaben" in reply or "Login f&uuml;r Member" in reply:
        return False
    return True
        
#        cookie.save( COOKIE_FILE, ignore_discard=True)
    
def get_image( station):
    return URL_BASE + "/img/station/%d/logo_s_big1.gif" % int(station)

def get_streamparams( station):
    html = fetchHttp( URL_BASE + "/tv/player/player.php?station_id=" + station)
    cid, cid2 = re.compile( "curChannel = '([0-9]*)'.*curDualChannel = '([0-9]*)'").findall( html)[0]

    hdrs = { "User-Agent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.17) Gecko/20110422 Ubuntu/10.04 (lucid) Firefox/3.6.17",
             "Referrer": URL_BASE + "/player/player.php"} 
    url = URL_BASE + "/tv/player/includes/ajax.php"
    args = { "cmd": "getLiveChannelParams", "cid": cid, "cid2": cid2 }
    
    req = urllib2.Request( url, urllib.urlencode( args), hdrs)
    r = urllib2.urlopen( req);
    ch, app, a, b, c, d, e, f = r.read().split( "|")[0:8] 

    link = "rtmp://62.65.136.20/nellotv"
    playpath = CHANNELS[station]
    url = link + " playpath=" + playpath + " swfvfy=true swfurl=" + PLAYER
    for i in a,b,c,d,e,f:
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
    soup = BeautifulSoup( fetchHttp( URL_BASE + "/tv/live_tv.php"))
    
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
            img = get_image( id)
            title = name + ": " + show
            if desc: title += " (+" + desc + ")"
            addDirectoryItem( title, { PARAMETER_KEY_STATION: str(id), PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_TITLE: title }, img)
#        print "%3d  %-10s %s (+%s)" % (id, name, show, desc)
    xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=True)


params = parameters_string_to_dict(sys.argv[2])
mode = params.get(PARAMETER_KEY_MODE, "0")

if not ensure_cookie():
    notify( "Login Failure!", "Please set your login/password in the addon settings")

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_PLAY:

    station = params[PARAMETER_KEY_STATION]
    url = get_streamparams( station)
    img = get_image( station)

    li = xbmcgui.ListItem( params[PARAMETER_KEY_TITLE], iconImage=img, thumbnailImage=img)
    li.setProperty( "IsPlayable", "true")
    li.setProperty( "Video", "true")

    xbmc.Player().play( url, li)
