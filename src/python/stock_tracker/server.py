#!/usr/bin/env python

import cherrypy
import os

from mako.lookup import TemplateLookup

from stock_tracker.apigateway import ApiGateway

class Root(ApiGateway):

    def __init__(self, show_debugger):
        super(Root, self).__init__()

        self.show_debugger = show_debugger
        templateDir = os.path.join(cherrypy.Application.wwwDir, 'templates')
        cherrypy.log("Template Dir: %s" % templateDir)
        self.templateLookup = TemplateLookup(directories=templateDir)

    # no authorization needed for the landing page
    @cherrypy.expose
    def index(self, *args):
        """
        This will redirect users to the proper view

        :return:
        """
        print(args)
        user = cherrypy.session.get("name", None)
        if user is None:
            print("no user, redirecting")
            # template = self.templateLookup.get_template("login.html")
            raise cherrypy.HTTPRedirect("/login")
        else:
            print("user present, redirecting")
            raise cherrypy.HTTPRedirect("/app#!#home")
            # template = self.templateLookup.get_template("app.html")
        # return template.render()

    @cherrypy.expose
    def login(self):
        """
        Return the login page
        """
        user = cherrypy.session.get("name", None)
        if user is not None:
            print("login redirect to app")
            raise cherrypy.HTTPRedirect("/")
        print("render login")
        template = self.templateLookup.get_template("login.html")
        return template.render()

    @cherrypy.expose
    def app(self):
        """
        Return the application page
        """
        print("render app")
        #verify user has been authenticated
        if cherrypy.session.get("name", None) is None:
            raise cherrypy.HTTPRedirect("/")
        return self.templateLookup.get_template("app.html").render()