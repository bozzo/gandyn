#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import getopt
import sys
import syslog
import xmlrpc.client

import ipretriever
import ipretriever.adapter

API_KEY = ''
DOMAIN_NAME = 'mydomain.com'
TTL = 300

RECORD = {'type': 'A', 'name': '@'}

LOG_LEVEL = syslog.LOG_INFO


class GandiDomainUpdater(object):
	"""Updates a gandi DNS record value."""
	
	def __init__(self, api_key, domain_name, record):
		"""Constructor
	
		Keyword arguments:
		api_key -- The gandi XML-RPC api key. You have to activate it on gandi website.
		domain_name -- The domain whose record will be updated
		record -- Filters that match the record to update
		"""
		self.api_key = api_key
		self.domain_name = domain_name
		self.record = record
		self.__api = xmlrpc.client.ServerProxy('https://rpc.gandi.net/xmlrpc/')
		self.__zone_id = None
	
	def __get_active_zone_id(self):
		"""Retrieve the domain active zone id."""
		if self.__zone_id is None:
			self.__zone_id = self.__api.domain.info(
				self.api_key,
				self.domain_name
			)['zone_id']
		return self.__zone_id
	
	def get_record_value(self):
		"""Retrieve current value for the record to update."""
		zone_id = self.__get_active_zone_id()
		return self.__api.domain.zone.record.list(
			self.api_key,
			zone_id,
			0,
			self.record
		)[0]['value']
	
	def update_record_value(self, new_value, ttl=300):
		"""Updates record value.
	
		Update is done on a new zone version. If an error occurs,
		that new zone is deleted. Else, it is activated.
		This is an attempt of rollback mechanism.
		"""
		new_zone_version = None
		zone_id = self.__get_active_zone_id()
		try:
			# create new zone version
			new_zone_version = self.__api.domain.zone.version.new(
				self.api_key,
				zone_id
			)
			syslog.syslog(syslog.LOG_DEBUG, 'DNS working on a new zone (version %s)' % new_zone_version)
			record_list = self.__api.domain.zone.record.list(
				self.api_key,
				zone_id,
				new_zone_version,
				self.record
			)
			# Update each record that matches the filter
			for a_record in record_list:
				# get record id
				a_record_id = a_record['id']
				a_record_name = a_record['name']
				a_record_type = a_record['type']
				
				# update record value
				new_record = self.record.copy()
				new_record.update({'name': a_record_name, 'type': a_record_type, 'value': new_value, 'ttl': ttl})
				self.__api.domain.zone.record.update(
					self.api_key,
					zone_id,
					new_zone_version,
					{'id': a_record_id},
					new_record
				)
		except xmlrpc.client.Fault:
			# delete updated zone
			if new_zone_version is not None:
				self.__api.domain.zone.version.delete(
					self.api_key,
					zone_id,
					new_zone_version
				)
			raise
		else:
			# activate updated zone
			self.__api.domain.zone.version.set(
				self.api_key,
				zone_id,
				new_zone_version
			)


def usage(argv):
	print(argv[0], ' [[-c | --config] <config file>] [-h | --help]')
	print('\t-c --config <config file> : Path to the config file')
	print('\t-h --help                 : Displays this text')


def main(argv, global_vars, local_vars):
	try:
		options, remainder = getopt.getopt(argv[1:], 'c:h', ['config=', 'help'])
		for opt, arg in options:
			if opt in ('-c', '--config'):
				config_file = arg
				# load config file
				exec(
					compile(open(config_file).read(), config_file, 'exec'),
					global_vars,
					local_vars
				)
			elif opt in ('-h', '--help'):
				usage(argv)
				exit(1)
	except getopt.GetoptError as e:
		print(e)
		usage(argv)
		exit(1)
	
	try:
		syslog.openlog("gandyn", syslog.LOG_PERROR, syslog.LOG_LOCAL0)
		syslog.setlogmask(syslog.LOG_UPTO(LOG_LEVEL))
		syslog.syslog(syslog.LOG_INFO, "Started")
		public_ip_retriever = ipretriever.adapter.Ipify()
		gandi_updater = GandiDomainUpdater(API_KEY, DOMAIN_NAME, RECORD)
		
		# get DNS record ip address
		previous_ip_address = gandi_updater.get_record_value()
		syslog.syslog(syslog.LOG_DEBUG, 'DNS record IP address : %s' % previous_ip_address)
		
		# get current ip address
		current_ip_address = public_ip_retriever.get_public_ip()
		syslog.syslog(syslog.LOG_DEBUG, 'Current public IP address : %s' % current_ip_address)
		
		if current_ip_address != previous_ip_address:
			# update record value
			gandi_updater.update_record_value(current_ip_address, TTL)
			syslog.syslog(syslog.LOG_INFO('DNS updated'))
		else:
			syslog.syslog(syslog.LOG_DEBUG, 'Public IP address unchanged. Nothing to do.')
		syslog.syslog(syslog.LOG_INFO, "Finished")
	except xmlrpc.client.Fault as e:
		syslog.syslog(syslog.LOG_ERR, 'An error occured using Gandi API : %s ' % e)
	except ipretriever.Fault as e:
		syslog.syslog(syslog.LOG_ERR, 'An error occured retrieving public IP address : %s' % e)


main(sys.argv, globals(), locals())
