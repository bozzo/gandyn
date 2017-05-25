#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import re
import urllib.request

import ipretriever


class Generic(object):
	def __init__(self, url_page):
		self.url_page = url_page
	
	def get_public_ip(self):
		"""Returns the current public IP address. Raises an exception if an issue occurs."""
		try:
			f = urllib.request.urlopen(self.url_page)
			data = f.read().decode("utf8")
			f.close()
			pattern = re.compile('\d+\.\d+\.\d+\.\d+')
			result = pattern.search(data, 0)
			if result is None:
				raise ipretriever.Fault('Service %s failed to return the current public IP address' % self.url_page)
			else:
				return result.group(0)
		except urllib.error.URLError as e:
			raise ipretriever.Fault(e)


class Ipify(Generic):
	def __init__(self):
		super(Ipify, self).__init__('https://api.ipify.org/?format=raw')


class WtfIsMyIp(Generic):
	def __init__(self):
		super(WtfIsMyIp, self).__init__('https://ipv4.wtfismyip.com/text')


class MyExternalIp(Generic):
	def __init__(self):
		super(MyExternalIp, self).__init__('https://ipv4.myexternalip.com/raw')
