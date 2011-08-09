# coding=UTF-8
#!/usr/bin/env python


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.api import users

from django.utils import simplejson
from datetime import datetime, timedelta


import os
import logging
import urllib
import md5

#TODO: usar MEMCACHE para armazenar a ultima verificação



class Parametros(db.Model):
	#key_name (“PARAMETROS”)
	access_token = db.StringProperty(default='')
	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	last_verify = db.DateTimeProperty()

class Link(db.Model):
	#key_name (MD5 da URL)
	url = db.LinkProperty(required=True)
	name = db.StringProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	shares = db.IntegerProperty(required=True, default=0)
	last_check = db.DateTimeProperty()
	enabled = db.BooleanProperty(default=True)
	user = db.UserProperty()

class Xbee(db.Model):
	#key_name (ad64H+ad64L+ad16)
	link = db.ReferenceProperty(Link, collection_name='xbees')
	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	name = db.StringProperty(required=True)
	address_h = db.StringProperty(required=True)
	address_l = db.StringProperty(required=True)
	#address_16 = db.StringProperty(required=True)
	new = db.BooleanProperty(required=True, default=True)



class LinkForm(djangoforms.ModelForm):
	class Meta:
		model = Link
		exclude = ['created', 'updates', 'shares', 'last_check', 'enabled', 'user']
	


"""

	URLs CALLS:

	/								gerenciador raiz, listagem dos links e xbees (marcando os novos) 
	/link/list/						json com lista de links
	/link/add/						json/post para adicionar link
	/link/enable/[key]/				json/post para habilitar link
	/link/disable/[key]/			json/post para desabilitar link
	/link/addxbee/[key]/[xbee]/		json/post para adicionar xbee ao link
	/link/delxbee/[key]/[xbee]/		json/post para remover xbee do link
	
	/xbee/list/						json lista xbees cadastrados
	/xbee/verify/[xbee]/			consulta dados ou inclui xbee específico (chamado pelo arduino)
									se o xbee nao possuir link vinculado retornar espacos
	
	/queue/verify_shares/ 			consulta API do facebook de todos os links cadastrados e habilitados

	tanto o /link/list/ quando /xbee/verify/ verificam e chamam a QUEUE para consultar no facebook.
	
"""

TEMPO_VERIFY_SHARES = timedelta(seconds=10)

parametros = Parametros.get_or_insert("PARAMETROS")


def verify_user():
	return not users.get_current_user() is None


class MainHandler(webapp.RequestHandler):
    def get(self):
		user = users.get_current_user()
		
		template_data = {}
		template_data['authenticated'] = not user is None
		template_data['admin'] = users.is_current_user_admin()
		template_data['nickname'] = not user is None and user.nickname() or ""
		template_data['user_id'] = not user is None and user.user_id() or ""
		template_data['email'] = not user is None and user.email() or ""
		
		template_data['add_form'] = LinkForm().as_ul()
		
		#user = users.get_current_user()
		if user is None:
			template_data['auth_url'] = users.create_login_url("/")
		else:
			template_data['auth_url'] = users.create_logout_url("/")
			
		path = os.path.join(os.path.dirname(__file__), 'template', 'main.html')
		self.response.out.write(template.render(path, template_data))
	


class QueueHandler(webapp.RequestHandler):
	def get(self, action=None):
		if (action is None):
			return
			
		if (action.lower() == "verify_shares"):
			logging.info("VERIFING SHARES...")
			self.response.out.write("VERIFY SHARES")
			parametros.last_verify = datetime.now()
			parametros.put()
			
			# verify shares no Facebook
			urls = []
			links = Link.all().filter("enabled =", True).fetch(1000)
			facebook_url = "https://graph.facebook.com/?access_token=%s&ids=%s" % (parametros.access_token, ','.join(str(urllib.quote(link.url)) for link in links))
			
			result = urlfetch.fetch(facebook_url)
			if result.status_code == 200:
				shares = simplejson.loads(result.content)
				for share in shares:
					logging.info(shares[share]["id"])
					key_name = md5.new(shares[share]["id"]).hexdigest()
					link = Link.get_by_key_name(key_name)
					if "shares" in shares[share]:
						link.shares = shares[share]["shares"]
					
					link.last_check = datetime.now()
					link.put()
		else:
			self.response.out.write("INVALID ACTION!")
	


class XbeeHandler(webapp.RequestHandler):
	def get(self, action=None, xbee_addr=None):
		#self.response.out.write("GET XBEE %s %s" % (action, xbee_addr or "-"))
		
		if (action is None):
			return
		
		if (action.lower() == "list"):
			if not verify_user():
				self.response.out.write("NOT AUTHENTICATED!")
				return
						
			# listar dispositivos
			xbees = Xbee.all().order('created').fetch(1000)
			lista = []
			for xbee in xbees:
				lista.append({
					"key_name": xbee.key().name(),
					"name": xbee.name,
					"link": xbee.link and xbee.link.key().name() or None,
					"created": xbee.created.isoformat(),
					"new": xbee.new
				})
				
			self.response.out.write(simplejson.dumps(lista))
			
		elif (action.lower() == "verify"):
			verify_time_to_generate_task()
			
			# retornar numero para dispositivo (arduino)
			xbee = Xbee.get_or_insert(
				xbee_addr,
				address_h = xbee_addr[0:8], 
				address_l = xbee_addr[8:16],
				name = "%s %s" % (xbee_addr[0:8], xbee_addr[8:16])
				#address_16 = xbee_addr[5:]
			)
			
			message = "\t%s\x1b"
			
			#TODO: rever parametros para retorno Arduino
			#self.response.out.write("\t%s\x99\b\b\b\b\x27" % (xbee_addr))
			#self.response.out.write(xbee.key().name())
			if (not xbee.link is None):
				logging.info("%s:% 4i" % (xbee.key().name(), xbee.link.shares))
				self.response.out.write("\t%s% 4i\x1b" % (xbee.key().name(), xbee.link.shares))
			else:
				logging.info("%s: %s" % (xbee.key().name(), ("----")))
				self.response.out.write("\t%s%s\x1b" % (xbee.key().name(), ("----")))
			
			
	
	def post(self, action=None, xbee_addr=None):
		self.get(action, xbee_addr)
		#self.response.out.write("POST XBEE %s %s" % (action, xbee_addr or "-"))
	


class LinkHandler(webapp.RequestHandler):
	def get(self, action=None, key_name=None, xbee_addr=None):
		#self.response.out.write("GET LINK %s %s %s" % (action, key_name or "-", xbee_addr or "-"))
		
		if (action is None):
			return
		
		if not verify_user():
			self.response.out.write("NOT AUTHENTICATED!")
			return
		
		if (action.lower() == "list"):
			verify_time_to_generate_task()
			links = Link.all().order('name').fetch(1000)
			lista = []
			for link in links:
				lista.append({
					"key_name": link.key().name(),
					"url": link.url, 
					"name": link.name, 
					"shares": link.shares, 
					"enabled": link.enabled
				})
			
			self.response.out.write(simplejson.dumps(lista))
			
		elif (action.lower() == "add"):
			formulario = LinkForm(data=self.request.POST)
			if not formulario.is_valid():
				retorno = {
					"ok": False,
					"mensagem": "Invalida data."
				}
				self.response.out.write(simplejson.dumps(retorno))
				return
				
			key_name = md5.new(formulario.data["url"]).hexdigest()
			link = Link.get_by_key_name(key_name)
			if (not link is None):
				# retorno erro
				retorno = {
					"ok": False,
					"mensagem": "The url %s has already on database." % formulario.data["url"]
				}
				self.response.out.write(simplejson.dumps(retorno))
				return

			#logging.info(data)
			link = formulario.save(commit=False)
			link._key_name = key_name
			link.user = users.get_current_user()
			link.put()
			retorno = {
				"ok": True
			}
			self.response.out.write(simplejson.dumps(retorno))
			
		else:
			link = Link.get_by_key_name(key_name)
			if (link is None):
				# retorno erro
				retorno = {
					"ok": False,
					"mensagem": "Link não encontrado."
				}
				self.response.out.write(simplejson.dumps(retorno))
				return
			
			if (action.lower() == "delete"):
				if (not users.is_current_user_admin()):
					# retorno erro
					retorno = {
						"ok": False,
						"mensagem": "Sem permissão de administrador."
					}
					self.response.out.write(simplejson.dumps(retorno))
					return
				
				for xbee in link.xbees:
					xbee.link = None
					xbee.put()
					
				link.delete()
				retorno = {
					"ok": True,
					"key_name": link.key().name()
				}
				self.response.out.write(simplejson.dumps(retorno))
				
				
			elif (action.lower() == "enable"):
				# enable de link
				link.enabled = True
				link.put()
				retorno = {
					"ok": True
				}
				self.response.out.write(simplejson.dumps(retorno))
				
			elif (action.lower() == "disable"):
				# disable de link
				link.enabled = False
				link.put()
				retorno = {
					"ok": True
				}
				self.response.out.write(simplejson.dumps(retorno))
				
			elif (action.lower() == "addxbee" or action.lower() == "delxbee"):
				xbee = Xbee.get_by_key_name(xbee_addr)
				if (xbee is None):
					# retorno erro
					retorno = {
						"ok": False,
						"mensagem": "Xbee não encontrado."
					}
					self.response.out.write(simplejson.dumps(retorno))
					return
					
				if (action.lower() == "addxbee"):
					# vincular xbee
					xbee.new = False
					xbee.link = link
					xbee.put()
					retorno = {
						"ok": True,
						"key_name": xbee.key().name()
					}
					self.response.out.write(simplejson.dumps(retorno))
					
				elif (action.lower() == "delxbee"):
					# desvincular xbee
					xbee.link = None
					xbee.put()
					retorno = {
						"ok": True,
						"key_name": xbee.key().name()
					}
					self.response.out.write(simplejson.dumps(retorno))
			else:
				retorno = {
					"ok": False,
					"mensagem": "Comanto inválido."
				}
				self.response.out.write(simplejson.dumps(retorno))
	
	
	def post(self, action=None, key_name=None, xbee_addr=None):
		self.get(action, key_name, xbee_addr)
		#self.response.out.write("POST LINK %s %s %s" % (action, key_name or "-", xbee_addr or "-"))

def verify_time_to_generate_task():
	# criar task para consultar shares no Facebook
	if (parametros.last_verify is None or datetime.now() - parametros.last_verify > TEMPO_VERIFY_SHARES):
		taskqueue.add(url="/queue/verify_shares/", method="GET")
	



def main():
	
	enderecos = [
		('/xbee/(list)/', XbeeHandler),
		('/xbee/(verify)/([A-F0-9]{16})/', XbeeHandler),
		('/link/(list|add)/', LinkHandler),
		('/link/(delete|enable|disable)/([^/]+)?/', LinkHandler),
		('/link/(addxbee|delxbee)/([^/]+)?/([A-F0-9]{16})/', LinkHandler),
		('/queue/(.*)/', QueueHandler),
		('.*', MainHandler),
	]
	application = webapp.WSGIApplication(enderecos, debug=True)
	util.run_wsgi_app(application)	

if __name__ == '__main__':
    main()
