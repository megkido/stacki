# @copyright@
# Copyright (c) 2006 - 2017 StackIQ Inc.
# All rights reserved. stacki(r) v5.0 stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
#

import os
import shlex
import subprocess
import stack.commands
from stack.exception import CommandError


class Implementation(stack.commands.Implementation):	
	"""
	Copy a SLES/CaaSP ISO to the frontend.
	"""

	def check_impl(self):
		# Check the DISTRO line in the content file
		# This should be of the format
		# DISTRO	   cpe:/o:suse:sles:12:sp2,SUSE Linux Enterprise Server 12 SP2
		#
		# or:
		#
		# DISTRO	cpe:/o:suse:caasp:1.0,SUSE Container as a Service Platform 1.0

		self.name = None
		self.vers = None
		self.release = None
		self.arch = 'x86_64'

		found_distro = False
		if os.path.exists('/mnt/cdrom/content'):
			file = open('/mnt/cdrom/content', 'r')

			for line in file.readlines():
				l = line.split(None, 1)
				if len(l) > 1:
					key = l[0].strip()
					value = l[1].strip()

					if key == 'DISTRO':
						a = value.split(',')
						v = a[0].split(':')
						relstring = a[1]
						
						if v[3] == 'sles':
							self.name = 'SLES'
						elif v[3] == 'caasp':
							self.name = 'CaaSP'
							self.release = 'suse'
						elif v[3] == 'sle-sdk':
							self.name = v[3].upper()

						if self.name:
							self.vers = v[4]
							if len(v) > 5:
								self.release = v[5]
							found_distro = True
						else:
							return False


			file.close()
		if not self.release:
			self.release = stack.release
		if found_distro:
			return True
		else:
			return False


	def run(self, args):
		import stack

		(clean, prefix)	 = args

		if not self.name:
			raise CommandError(self, 'unknown SLES/CaaSP on media')
		if not self.vers:
			raise CommandError(self, 'unknown SLES/CaaSP version on media')
			
		OS = 'sles'
		roll_dir = os.path.join(prefix, self.name, self.vers, self.release, OS, self.arch)
		destdir = roll_dir

		if clean and os.path.exists(roll_dir):
			print('Cleaning %s version %s ' % (self.name, self.vers), end=' ')
			print('for %s from pallets directory' % self.arch)
			os.system('/bin/rm -rf %s' % roll_dir)
			os.makedirs(roll_dir)

		print('Copying "%s" (%s,%s) pallet ...' % (self.name, self.vers, self.arch))

		if not os.path.exists(destdir):
			os.makedirs(destdir)

		cmd = 'rsync -a --exclude "TRANS.TBL" %s/ %s/' \
			% (self.owner.mountPoint, destdir)
		subprocess.call(shlex.split(cmd))

		#
		# Copy pallet patches into the respective pallet
		# directory
		#
		print('Patching %s pallet' % self.name)
		patch_dir = '/opt/stack/%s-pallet-patches/%s' % \
			(self.name, self.vers)
		cmd = 'rsync -a %s/ %s/' % (patch_dir, destdir)
		subprocess.call(shlex.split(cmd))

		#
		# create roll-<name>.xml file
		#
		xmlfile = open('%s/roll-%s.xml' % (roll_dir, self.name), 'w')

		xmlfile.write('<roll name="%s" interface="6.0.2">\n' % self.name)
		xmlfile.write('<color edge="white" node="white"/>\n')
		xmlfile.write('<info version="%s" release="%s" arch="%s" os="%s"/>\n' % (self.vers, self.release, self.arch, OS))
		xmlfile.write('<iso maxsize="0" addcomps="0" bootable="0"/>\n')
		xmlfile.write('<rpm rolls="0" bin="1" src="0"/>\n')
		xmlfile.write('</roll>\n')

		xmlfile.close()

		return (self.name, self.vers, self.release, self.arch, OS)

