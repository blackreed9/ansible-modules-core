#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2012, Red Hat, inc
# Written by Seth Vidal
# based on the mount modules from salt and puppet
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: mount
short_description: Control active and configured mount points
description:
     - This module controls active and configured mount points in C(/etc/fstab).
version_added: "0.6"
options:
  name:
    description:
      - "path to the mount point, eg: C(/mnt/files)"
    required: true
    default: null
    aliases: []
  src:
    description:
      - device to be mounted on I(name).
    required: true
    default: null
  fstype:
    description:
      - file-system type
    required: true
    default: null
  opts:
    description:
      - mount options (see fstab(8))
    required: false
    default: null
  dump:
    description:
      - "dump (see fstab(8)), Note that if nulled, C(state=present) will cease to work and duplicate entries will be made with subsequent runs."
    required: false
    default: 0
  passno:
    description:
      - "passno (see fstab(8)), Note that if nulled, C(state=present) will cease to work and duplicate entries will be made with subsequent runs."
    required: false
    default: 0
  state:
    description:
      - C(absent): remove the entry from the C(fstab) file
      - C(present): add an entry to the C(fstab) file
      - C(unmounted): remove the entry from the C(fstab) file, unmount the file system (C(src)), and remove the mount point (C(name))
      - C(mounted): add an entry to the fstab file, create the mount point (C(name)) if needed, and mount the file system (C(src))
    required: true
    choices: [ "present", "absent", "mounted", "unmounted" ]
    default: null
  fstab:
    description:
      - file to use instead of C(/etc/fstab). You shouldn't use that option
        unless you really know what you are doing. This might be useful if
        you need to configure mountpoints in a chroot environment.
    required: false
    default: /etc/fstab

notes: []
requirements: []
author: Seth Vidal
'''
EXAMPLES = '''
# Mount DVD read-only
- mount: name=/mnt/dvd src=/dev/sr0 fstype=iso9660 opts=ro state=present

# Mount up device by label
- mount: name=/srv/disk src='LABEL=SOME_LABEL' fstype=ext4 state=present

# Mount up device by UUID
- mount: name=/home src='UUID=b3e48f45-f933-4c8e-a700-22a159ec9077' fstype=xfs opts=noatime state=present
'''


def write_fstab(lines, dest):

    fs_w = open(dest, 'w')
    for l in lines:
        fs_w.write(l)

    fs_w.flush()
    fs_w.close()

def set_mount(**kwargs):
    """ set/change a mount point location in fstab """

    # kwargs: name, src, fstype, opts, dump, passno, state, fstab=/etc/fstab
    args = dict(
        opts   = 'defaults',
        dump   = '0',
        passno = '0',
        fstab  = '/etc/fstab'
    )
    args.update(kwargs)

    new_line = '%(src)s %(name)s %(fstype)s %(opts)s %(dump)s %(passno)s\n'

    to_write = []
    exists = False
    changed = False
    for line in open(args['fstab'], 'r').readlines():
        if not line.strip():
            to_write.append(line)
            continue
        if line.strip().startswith('#'):
            to_write.append(line)
            continue
        if len(line.split()) != 6:
            # The fstab file has 6 fields anything that does not is non-standard
            #  and is safely saved but not processed
            to_write.append(line)
            continue

        ld = {}
        ld['src'], ld['name'], ld['fstype'], ld['opts'], ld['dump'], ld['passno']  = line.split()

        if ld['name'] != args['name']:
            to_write.append(line)
            continue

        # it exists - now see if what we have is different
        exists = True
        for t in ('src', 'fstype','opts', 'dump', 'passno'):
            if ld[t] != args[t]:
                changed = True
                ld[t] = args[t]

        if changed:
            to_write.append(new_line % ld)
        else:
            to_write.append(line)

    if not exists:
        to_write.append(new_line % args)
        changed = True

    if changed:
        write_fstab(to_write, args['fstab'])

    return changed

def unset_mount(**kwargs):
    """ remove a mount point from fstab """

    # kwargs: name, src, fstype, opts, dump, passno, state, fstab=/etc/fstab
    args = dict(
        opts   = 'default',
        dump   = '0',
        passno = '0',
        fstab  = '/etc/fstab'
    )
    args.update(kwargs)

    to_write = []
    changed = False
    for line in open(args['fstab'], 'r').readlines():
        if not line.strip():
            to_write.append(line)
            continue
        if line.strip().startswith('#'):
            to_write.append(line)
            continue
        if len(line.split()) != 6:
            # not sure what this is or why it is here
            # but it is not our fault so leave it be
            to_write.append(line)
            continue

        ld = {}
        ld['src'], ld['name'], ld['fstype'], ld['opts'], ld['dump'], ld['passno']  = line.split()

        if ld['name'] != args['name']:
            to_write.append(line)
            continue

        # if we got here we found a match - continue and mark changed
        changed = True

    if changed:
        write_fstab(to_write, args['fstab'])

    return changed

def mount_fs(module, **kwargs):
    """ mount up a path or remount if needed """
    mount_bin = module.get_bin_path('mount')

    name = kwargs['name']
    if os.path.ismount(name):
        cmd = [ mount_bin , '-o', 'remount', name ]
    else:
        cmd = [ mount_bin, name ]

    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return 0, ''
    else:
        return rc, out+err

def umount_fs(module, **kwargs):
    """ unmount a path """

    umount_bin = module.get_bin_path('umount')
    name = kwargs['name']
    cmd = [umount_bin, name]

    rc, out, err = module.run_command(cmd)
    if rc == 0:
        return 0, ''
    else:
        return rc, out+err

def get_mounted_fs(module):
    mounted = {}
    rc, out, err = module.run_command('mount -l')
    if rc == 0:
        for mount in out.split("\n")[:-1]:
            fields = mount.split()
            mounted[fields[2]] = fields[0]
    return mounted


def main():

    module = AnsibleModule(
        argument_spec = dict(
            state  = dict(required=True, choices=['present', 'absent', 'mounted', 'unmounted']),
            name   = dict(required=True),
            opts   = dict(default=None),
            passno = dict(default=None),
            dump   = dict(default=None),
            src    = dict(required=True),
            fstype = dict(required=True),
            fstab  = dict(default='/etc/fstab')
        )
    )


    changed = False
    rc = 0
    args = {
        'name': module.params['name'],
        'src': module.params['src'],
        'fstype': module.params['fstype'],
        'state': module.params['state']
    }
    if module.params['passno'] is not None:
        args['passno'] = module.params['passno']
    if module.params['opts'] is not None:
        if ' ' in module.params['opts']:
            module.fail_json(msg="unexpected space in 'opts' parameter")
        args['opts'] = module.params['opts']
    if module.params['dump'] is not None:
        args['dump'] = module.params['dump']
    if module.params['fstab'] is not None:
        args['fstab'] = module.params['fstab']

    mounted_fs = get_mounted_fs(module)
    if not mounted_fs:
        module.fail_json(msg="Error getting list of mounted file systems")

    # if fstab file does not exist, we first need to create it. This mainly
    # happens when fstab option is passed to the module.
    if not os.path.exists(args['fstab']):
        if not os.path.exists(os.path.dirname(args['fstab'])):
            os.makedirs(os.path.dirname(args['fstab']))
        open(args['fstab'],'a').close()

    if args['state'] == 'absent':
        changed = unset_mount(**args)
        module.exit_json(changed=changed, **args)

    if args['state'] == 'present':
        changed = set_mount(**args)
        module.exit_json(changed=changed, **args)

    if args['state'] == 'unmounted':
        changed = unset_mount(**args)

        if args['name'] in mounted_fs:
            rc, msg  = umount_fs(module, **args)
            if rc:
                module.fail_json(msg="Error unmounting %s: %s" % (args['name'], msg))
            changed = True

        # In the event the file system wasn't mounted, but the mount point still 
        #   exists we should try to remove it
        if os.path.exists(args['name']):
            try:
                # We are using rmdir() in case there was data under the mount point
                #   the user may not want to lose it.
                os.rmdir(args['name'])
                changed = True
            except (OSError), e:
                module.fail_json(msg="Error removing mount point %s: %s" % (args['name'], str(e)))

        module.exit_json(changed=changed, **args)

    if args['state'] == 'mounted':
        changed = set_mount(**args)

        if not os.path.exists(args['name']):
            try:
                os.makedirs(args['name'])
                changed = True
            except (OSError, IOError), e:
                unset_mount(**args)
                module.fail_json(msg="Error making dir %s: %s" % (args['name'], str(e)))


        if args['name'] not in mounted_fs or changed:
            rc, msg = mount_fs(module, **args)
            if rc:
                unset_mount(**args)
                module.fail_json(msg="Error mounting %s: %s" % (args['name'], msg))

        module.exit_json(changed=changed, **args)

    module.fail_json(msg='Unexpected position reached')
    sys.exit(0)

# import module snippets
from ansible.module_utils.basic import *
main()
