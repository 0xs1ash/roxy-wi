import json

import modules.db.sql as sql
import modules.server.ssh as mod_ssh
import modules.common.common as common
import modules.roxywi.auth as roxywi_auth
import modules.roxywi.common as roxywi_common

form = common.form


def ssh_command(server_ip: str, commands: list, **kwargs):
	if server_ip == '':
		return 'error: IP cannot be empty'
	if kwargs.get('timeout'):
		timeout = kwargs.get('timeout')
	else:
		timeout = 1
	try:
		with mod_ssh.ssh_connect(server_ip) as ssh:
			for command in commands:
				try:
					stdin, stdout, stderr = ssh.run_command(command, timeout=timeout)
				except Exception as e:
					print(f'error: {e}')
					roxywi_common.logging('Roxy-WI server', f' Something wrong with SSH connection. Probably sudo with password {e}', roxywi=1)
					return str(e)

				if stderr:
					for line in stderr.readlines():
						if line:
							print(f'error: {line}')
							roxywi_common.logging('Roxy-WI server', f' {line}', roxywi=1)

				try:
					if kwargs.get('raw'):
						return stdout.readlines()
					if kwargs.get("ip") == "1":
						show_ip(stdout)
					elif kwargs.get("show_log") == "1":
						import modules.roxywi.logs as roxywi_logs

						return roxywi_logs.show_log(stdout, grep=kwargs.get("grep"))
					elif kwargs.get('return_err') == 1:
						return stderr.read().decode(encoding='UTF-8')
					else:
						return stdout.read().decode(encoding='UTF-8')
				except Exception as e:
					roxywi_common.logging('Roxy-WI server', f' Something wrong with SSH connection. Probably sudo with password {e}', roxywi=1)
	except Exception as e:
		roxywi_common.logging('Roxy-WI server', f' Something wrong with SSH connection: {e}', roxywi=1)
		raise Exception(f'error: {e}')


def subprocess_execute(cmd):
	import subprocess
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
	stdout, stderr = p.communicate()
	output = stdout.splitlines()

	return output, stderr


def is_file_exists(server_ip: str, file: str) -> bool:
	cmd = [f'[ -f {file} ] && echo yes || echo no']

	out = ssh_command(server_ip, cmd)
	return True if 'yes' in out else False


def is_service_active(server_ip: str, service_name: str) -> bool:
	cmd = [f'systemctl is-active {service_name}']

	out = ssh_command(server_ip, cmd)
	out = out.strip()
	return True if 'active' == out else False


def get_remote_files(server_ip: str, config_dir: str, file_format: str):
	config_dir = common.return_nice_path(config_dir)
	if file_format == 'conf':
		commands = [f'sudo ls {config_dir}*/*.{file_format}']
	else:
		commands = [f'sudo ls {config_dir}|grep {file_format}$']
	config_files = ssh_command(server_ip, commands)

	return config_files


def show_ip(stdout):
	for line in stdout:
		if "Permission denied" in line:
			print(f'error: {line}')
		else:
			print(line)


def get_system_info(server_ip: str) -> str:
	server_ip = common.is_ip_or_dns(server_ip)
	if server_ip == '':
		return 'error: IP cannot be empty'

	server_id = sql.select_server_id_by_ip(server_ip)

	command = ["sudo lshw -quiet -json"]
	try:
		sys_info_returned = ssh_command(server_ip, command, timeout=5)
	except Exception as e:
		raise e
	command = ['sudo hostnamectl |grep "Operating System"|awk -F":" \'{print $2}\'']
	try:
		os_info = ssh_command(server_ip, command)
	except Exception as e:
		raise e
	os_info = os_info.strip()
	system_info = json.loads(sys_info_returned)

	sys_info = {'hostname': system_info['id'], 'family': ''}
	cpu = {'cpu_model': '', 'cpu_core': 0, 'cpu_thread': 0, 'hz': 0}
	network = {}
	ram = {'slots': 0, 'size': 0}
	disks = {}

	try:
		sys_info['family'] = system_info['configuration']['family']
	except Exception:
		pass

	for i in system_info['children']:
		if i['class'] == 'network':
			try:
				ip = i['configuration']['ip']
			except Exception:
				ip = ''
			network[i['logicalname']] = {
				'description': i['description'],
				'mac': i['serial'],
				'ip': ip
			}
		for k, j in i.items():
			if isinstance(j, list):
				for b in j:
					try:
						if b['class'] == 'processor':
							cpu['cpu_model'] = b['product']
							cpu['cpu_core'] += 1
							cpu['hz'] = round(int(b['capacity']) / 1000000)
							try:
								cpu['cpu_thread'] += int(b['configuration']['threads'])
							except Exception:
								cpu['cpu_thread'] = 1
					except Exception:
						pass

					try:
						if b['id'] == 'memory':
							ram['size'] = round(b['size'] / 1073741824)
							for memory in b['children']:
								ram['slots'] += 1
					except Exception:
						pass

					try:
						if b['class'] == 'storage':
							for p, pval in b.items():
								if isinstance(pval, list):
									for disks_info in pval:
										for volume_info in disks_info['children']:
											if isinstance(volume_info['logicalname'], list):
												volume_name = volume_info['logicalname'][0]
												mount_point = volume_info['logicalname'][1]
												size = round(volume_info['capacity'] / 1073741824)
												size = str(size) + 'Gb'
												fs = volume_info['configuration']['mount.fstype']
												state = volume_info['configuration']['state']
												disks[volume_name] = {
													'mount_point': mount_point,
													'size': size,
													'fs': fs,
													'state': state
												}
					except Exception:
						pass

					try:
						if b['class'] == 'bridge':
							if 'children' in b:
								for s in b['children']:
									if s['class'] == 'network':
										if 'children' in s:
											for net in s['children']:
												network[net['logicalname']] = {
													'description': net['description'],
													'mac': net['serial']
												}
									if s['class'] == 'storage':
										for p, pval in s.items():
											if isinstance(pval, list):
												for disks_info in pval:
													if 'children' in disks_info:
														for volume_info in disks_info['children']:
															if isinstance(volume_info['logicalname'], dict):
																volume_name = volume_info['logicalname'][0]
																mount_point = volume_info['logicalname'][1]
																size = round(volume_info['size'] / 1073741824)
																size = str(size) + 'Gb'
																fs = volume_info['configuration']['mount.fstype']
																state = volume_info['configuration']['state']
																disks[volume_name] = {
																	'mount_point': mount_point,
																	'size': size,
																	'fs': fs,
																	'state': state
																}
									for z, n in s.items():
										if isinstance(n, list):
											for y in n:
												if y['class'] == 'network':
													try:
														for q in y['children']:
															try:
																ip = q['configuration']['ip']
															except Exception:
																ip = ''
															network[q['logicalname']] = {
																'description': q['description'],
																'mac': q['serial'],
																'ip': ip}
													except Exception:
														try:
															network[y['logicalname']] = {
																'description': y['description'],
																'mac': y['serial'],
																'ip': y['configuration']['ip']}
														except Exception:
															pass
												if y['class'] == 'disk':
													try:
														for q in y['children']:
															try:
																if isinstance(q['logicalname'], list):
																	volume_name = q['logicalname'][0]
																	mount_point = q['logicalname'][1]
																	size = round(q['capacity'] / 1073741824)
																	size = str(size) + 'Gb'
																	fs = q['configuration']['mount.fstype']
																	state = q['configuration']['state']
																	disks[volume_name] = {
																		'mount_point': mount_point,
																		'size': size,
																		'fs': fs,
																		'state': state
																	}
															except Exception as e:
																print(e)
													except Exception:
														pass
												if y['class'] == 'storage' or y['class'] == 'generic':
													try:
														for q in y['children']:
															for o in q['children']:
																try:
																	volume_name = o['logicalname']
																	mount_point = ''
																	size = round(o['size'] / 1073741824)
																	size = str(size) + 'Gb'
																	fs = ''
																	state = ''
																	disks[volume_name] = {
																		'mount_point': mount_point,
																		'size': size,
																		'fs': fs,
																		'state': state
																	}
																except Exception:
																	pass
																for w in o['children']:
																	try:
																		if isinstance(w['logicalname'], list):
																			volume_name = w['logicalname'][0]
																			mount_point = w['logicalname'][1]
																			try:
																				size = round(w['size'] / 1073741824)
																				size = str(size) + 'Gb'
																			except Exception:
																				size = ''
																			fs = w['configuration']['mount.fstype']
																			state = w['configuration']['state']
																			disks[volume_name] = {
																				'mount_point': mount_point,
																				'size': size,
																				'fs': fs,
																				'state': state
																			}
																	except Exception:
																		pass
													except Exception:
														pass
													try:
														for q, qval in y.items():
															if isinstance(qval, list):
																for o in qval:
																	for w in o['children']:
																		if isinstance(w['logicalname'], list):
																			volume_name = w['logicalname'][0]
																			mount_point = w['logicalname'][1]
																			size = round(w['size'] / 1073741824)
																			size = str(size) + 'Gb'
																			fs = w['configuration']['mount.fstype']
																			state = w['configuration']['state']
																			disks[volume_name] = {
																				'mount_point': mount_point,
																				'size': size,
																				'fs': fs,
																				'state': state
																			}
													except Exception:
														pass
					except Exception:
						pass

	try:
		sql.insert_system_info(server_id, os_info, sys_info, cpu, ram, network, disks)
	except Exception as e:
		raise e


def show_system_info() -> None:
	from jinja2 import Environment, FileSystemLoader

	server_ip = form.getvalue('server_ip')
	server_ip = common.is_ip_or_dns(server_ip)
	server_id = form.getvalue('server_id')

	if server_ip == '':
		print('error: IP or DNS name is not valid')
		return

	env = Environment(loader=FileSystemLoader('templates/'), autoescape=True,
					  extensions=["jinja2.ext.loopcontrols", "jinja2.ext.do"])
	env.globals['string_to_dict'] = common.string_to_dict
	template = env.get_template('ajax/show_system_info.html')
	if sql.is_system_info(server_id):
		try:
			get_system_info(server_ip)
			system_info = sql.select_one_system_info(server_id)

			template = template.render(system_info=system_info, server_ip=server_ip, server_id=server_id)
			print(template)
		except Exception as e:
			print(f'Cannot update server info: {e}')
	else:
		system_info = sql.select_one_system_info(server_id)

		template = template.render(system_info=system_info, server_ip=server_ip, server_id=server_id)
		print(template)


def update_system_info() -> None:
	from jinja2 import Environment, FileSystemLoader

	server_ip = form.getvalue('server_ip')
	server_ip = common.is_ip_or_dns(server_ip)
	server_id = form.getvalue('server_id')

	if server_ip == '':
		print('error: IP or DNS name is not valid')
		return

	sql.delete_system_info(server_id)

	env = Environment(loader=FileSystemLoader('templates/'), autoescape=True,
					  extensions=["jinja2.ext.loopcontrols", "jinja2.ext.do"])
	env.globals['string_to_dict'] = common.string_to_dict
	template = env.get_template('ajax/show_system_info.html')

	try:
		get_system_info(server_ip)
		system_info = sql.select_one_system_info(server_id)

		template = template.render(system_info=system_info, server_ip=server_ip, server_id=server_id)
		print(template)
	except Exception as e:
		print(f'error: Cannot update server info: {e}')


def show_firewalld_rules() -> None:
	from jinja2 import Environment, FileSystemLoader

	serv = common.checkAjaxInput(form.getvalue('viewFirewallRules'))

	cmd = ["sudo iptables -L INPUT -n --line-numbers|sed 's/  */ /g'|grep -v -E 'Chain|target'"]
	cmd1 = ["sudo iptables -L IN_public_allow -n --line-numbers|sed 's/  */ /g'|grep -v -E 'Chain|target'"]
	cmd2 = ["sudo iptables -L OUTPUT -n --line-numbers|sed 's/  */ /g'|grep -v -E 'Chain|target'"]

	input_chain = ssh_command(serv, cmd, raw=1)

	input_chain2 = []
	for each_line in input_chain:
		input_chain2.append(each_line.strip('\n'))

	if 'error:' in input_chain:
		print(input_chain)
		return

	in_public_allow = ssh_command(serv, cmd1, raw=1)
	output_chain = ssh_command(serv, cmd2, raw=1)
	env = Environment(loader=FileSystemLoader('templates'))
	template = env.get_template('ajax/firewall_rules.html')
	template = template.render(input=input_chain2, IN_public_allow=in_public_allow, output=output_chain)
	print(template)


def create_server(hostname, ip, group, typeip, enable, master, cred, port, desc, haproxy, nginx, apache, firewall, scan_server, **kwargs) -> bool:
	if not roxywi_auth.is_admin(level=2, role_id=kwargs.get('role_id')):
		raise Exception('not enough permission')

	if sql.add_server(hostname, ip, group, typeip, enable, master, cred, port, desc, haproxy, nginx, apache, firewall):
		try:
			if scan_server == '1':
				nginx_config_path = sql.get_setting('nginx_config_path')
				haproxy_config_path = sql.get_setting('haproxy_config_path')
				haproxy_dir = sql.get_setting('haproxy_dir')
				apache_config_path = sql.get_setting('apache_config_path')
				keepalived_config_path = sql.get_setting('keepalived_config_path')

				if is_file_exists(ip, nginx_config_path):
					sql.update_nginx(ip)

				if is_file_exists(ip, haproxy_config_path):
					sql.update_haproxy(ip)

				if is_file_exists(ip, keepalived_config_path):
					sql.update_keepalived(ip)

				if is_file_exists(ip, apache_config_path):
					sql.update_apache(ip)

				if is_file_exists(ip, haproxy_dir + '/waf/bin/modsecurity'):
					sql.insert_waf_metrics_enable(ip, "0")
					sql.insert_waf_rules(ip)

				if is_service_active(ip, 'firewalld'):
					sql.update_firewall(ip)

		except Exception as e:
			roxywi_common.logging(f'Cannot scan a new server {hostname}', str(e), roxywi=1)
			raise Exception(f'error: Cannot scan a new server {hostname} {e}')

		try:
			sql.insert_new_checker_setting_for_server(ip)
		except Exception as e:
			roxywi_common.logging(f'Cannot insert Checker settings for {hostname}', str(e), roxywi=1)
			raise Exception(f'error: Cannot insert Checker settings for {hostname} {e}')

		try:
			get_system_info(ip)
		except Exception as e:
			roxywi_common.logging(f'Cannot get information from {hostname}', str(e), roxywi=1, login=1)
			raise Exception(f'error: Cannot get information from {hostname} {e}')

		return True
	else:
		return False
