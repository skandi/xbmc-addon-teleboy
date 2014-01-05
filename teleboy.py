
import os, re, sys
import cookielib, urllib, urllib2
from cookielib import FileCookieJar
import xbmcgui, xbmcplugin, xbmcaddon
from mindmade import *
import simplejson
from BeautifulSoup import BeautifulSoup

__author__     = "Andreas Wetzel"
__copyright__  = "Copyright 2011-2013, mindmade.org"
__credits__    = [ "Francois Marbot" ]
__maintainer__ = "Andreas Wetzel"
__email__      = "xbmc@mindmade.org"

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

MODE_PLAY = "play"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_CID = "cid"
PARAMETER_KEY_CID2 = "cid2"
PARAMETER_KEY_TITLE = "title"

URL_BASE = "http://www.teleboy.ch"
URL_BASE_MEDIA = "http://media.cinergy.ch"
PLAYER = URL_BASE + "/assets/swf/flowplayer_ova/flowplayer.commercial-3.2.16.swf"
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
#       log( "cached cookies found!")
        for c in cookie:
            if c.name == "cinergy_auth":
#               log( "auth cookie found!")
                return True
    except IOError:
        pass
    cookie.clear()
    fetchHttp( URL_BASE + "/watchlist")
    log ( repr( cookie))
    log( "logging in...")
    login = settings.getSetting( id="login")
    password = settings.getSetting( id="password")
    url = URL_BASE + "/layer/login_check"
    args = { "login": login,
             "password": password,
             "keep_login": "1",
             "x": "3", "y": "4" }
    
    reply = fetchHttp( url, args, post=True);
    
    if "Falsche Eingaben" in reply or "Anmeldung war nicht erfolgreich" in reply:
        log( "login failure")
        log( reply)
        notify( "Login Failure!", "Please set your login/password in the addon settings")
        xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=False)
        return False
    res = cookie.save( ignore_discard=True)
    log( "login ok")
    return True
        

def getUrl( url, args={}, hdrs={}, post=False):
    url = URL_BASE + url
    if ensure_cookie():
        html = fetchHttp( url, args, hdrs, post)
        if "Bitte melde dich neu an" in html:
            os.unlink( xbmc.translatePath( COOKIE_FILE));
            if not ensure_cookie():
                return "";
            html = fetchHttp( url, args, hdrs, post)
        return html
    return ""

def get_stationLogo( station):
    return URL_BASE_MEDIA + "/t_station/%d/logo_s_big1.gif" % int(station)

def get_streamparams( station, cid, cid2):
    hdrs = { "Referer": URL_BASE + "/tv/player/player.php" } 
    url = "/tv/player/ajax/liveChannelParams"
    args = { "cid": cid, "cid2": cid2 }

    ans = getUrl( url, args, hdrs, False)
    json = simplejson.loads( ans)
    drm = json["params"]["drm"]
    params = drm.split('|');

    link = params[1]
    playpath = params[0]
    return "%s playpath=%s swfurl=%s swfvfy=true live=true" % (link, playpath, PLAYER)

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
    
    table = soup.find( "table", "show-listing")
    if not table: return
    for tr in table.findAll( "tr"):
        a = tr.find( "a", "playIcon")
        if a:
            try:
                id = int( a["data-stationid"])
                channel = htmldecode( tr.find( "td", "station").find( "img")["alt"])
                details = tr.find( "td", "showDetails")
                if (details.find( "a")):
                    show = htmldecode( details.find( "a")["title"])
                else:
                    show = details.text
                cid, cid2 = tr.find( "a", "playIcon")["data-play-live"].split("/")
                img = get_stationLogo( id)
                title = label = channel + ": " + show
                p = tr.find( "p", "listing_info");
                if p:
                    desc = p.text.replace( "|", "| ")
                    label = label + " (+" + desc + ")"
                addDirectoryItem( label, { PARAMETER_KEY_STATION: str(id), PARAMETER_KEY_CID: cid, PARAMETER_KEY_CID2: cid2,
                                 PARAMETER_KEY_MODE: MODE_PLAY, PARAMETER_KEY_TITLE: title }, img)
            except Exception as e:
                log( "Exception: " + str(e))
                log( "HTML(show): " + str( tr))
#        print "%3d  %-10s %s (+%s)" % (id, name, show, desc)
    xbmcplugin.endOfDirectory( handle=pluginhandle, succeeded=True)

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

elif mode == MODE_PLAY:

    station = params[PARAMETER_KEY_STATION]
    cid = params[PARAMETER_KEY_CID]
    cid2 = params[PARAMETER_KEY_CID2]
    url = get_streamparams( station, cid, cid2)
    if not url: exit( 1)
    img = get_stationLogo( station)

    li = xbmcgui.ListItem( params[PARAMETER_KEY_TITLE], iconImage=img, thumbnailImage=img)
    li.setProperty( "IsPlayable", "true")
    li.setProperty( "Video", "true")

    xbmc.Player().play( url, li)
