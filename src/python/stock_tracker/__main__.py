#!/usr/bin/env python3

import cherrypy, os, shutil

from stock_tracker.server import Root

def main():
    #create the download folder if it does not exist
    downloadDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.join('..', 'download'))
    if not os.path.exists(downloadDir):
        os.makedirs(downloadDir)
    else:
        #remove everything in the downloads folder
        shutil.rmtree(downloadDir, ignore_errors=True)
        os.makedirs(downloadDir)

    #configure the cherrypy server
    cherrypy.Application.wwwDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
        os.path.join('..', '..', 'www'))

    # cherrypy.Application.downloadDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
    #     os.path.join('..', 'download'))

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "conf"), "r") as f:
        a = f.readline().strip()
        if a == "PRODUCTION":
            confFile = "server-prod.conf"
        elif a == "DEVELOPMENT":
            confFile = "server-dev.conf"
        else:
            print("INVALID CONF: MUST BE 'PRODUCTION' or 'DEVELOPMENT'")
            return
    server_config = os.path.abspath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', '..', 'etc', confFile))

    #cherrypy.config.update({"engine.autoreload_on": True})
    cherrypy.config.update(server_config)
    cherrypy.tree.mount(
        Root(show_debugger=True),
        '/',
        config=server_config)

    # cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.engine.start()
    cherrypy.engine.block()
    '''
    # so windows users can exit gracefully
    windows = not os.path.exists('./.notwindows')

    if windows:
        input()
        cherrypy.engine.stop()
    else: #linux
        cherrypy.engine.block()
    '''
if __name__ == '__main__':
    main()
