#!/usr/bin/python
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

# This is a DOCUMENTATION stub specific to this module, it extends
# a documentation fragment located in ansible.utils.module_docs_fragments
DOCUMENTATION = '''
---
module: rax_images
short_description: Manipulate Rackspace Cloud Server Images
description:
  - Manipulate Rackspace Cloud Server Images
version_added: "2.0"
options:
  name:
    description:
      - Name of server from which image will be created
    default: null
  id:
    description:
      - Server ID from which image will be created
    default: null
  image_name:
    description:
      - Name of image which will be created
    required: true
  wait:
    description:
      - wait for the image to be in state 'active' before returning
    default: "no"
    choices:
      - "yes"
      - "no"
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 300

author: Vladimir Saienko
extends_documentation_fragment: rackspace
'''

EXAMPLES = '''
- name: Build server image in Rackspace
  local_action:
    module: rax_images
    credentials: ~/.raxpub
    name: "{{ inventory_hostname }}"
    image_name: "{{ image_name }}"
    region: DFW
    wait: yes
    wait_timeout: 300
'''

try:
    import pyrax
    HAS_PYRAX = True
except ImportError:
    HAS_PYRAX = False


def rax_images(module, name, server_id, image_name, wait=True, wait_timeout=300):
    changed = False

    cs = pyrax.cloudservers
    imgs = pyrax.images

    if cs is None:
        module.fail_json(msg='Failed to instantiate client. This '
                             'typically indicates an invalid region or an '
                             'incorrectly capitalized region name.')

    search_opts = {}
    if name:
        search_opts = dict(name='^%s$' % name)
        try:
            servers = cs.servers.list(search_opts=search_opts)
        except Exception, e:
            module.fail_json(msg='%s' % e.message)

    elif server_id:
        servers = []
        try:
            servers.append(cs.servers.get(server_id))
        except Exception, e:
            pass

    if len(servers) > 1:
        module.fail_json(msg='Multiple servers found matching provided '
                             'search parameters')
    elif not servers:
        module.fail_json(msg='Failed to find a server matching provided '
                             'search parameters')

    server = servers[0]
    image_id = cs.servers.create_image(server, image_name)
    image =[]

    if wait:
        end_time = time.time() + wait_timeout
        infinite = wait_timeout == 0
        while infinite or time.time() < end_time:
            try:
                # Match image name and ID of newly created image since name is not unique
                image_data = [img for img in imgs.list()
                          if name in img.name and image_id in img.id]
            except:
                image.status == 'ERROR'
                if not filter(lambda s: s.status not in FINAL_STATUSES,
                              image_data):
                    break
                time.sleep(5)

    success = []
    error = []
    timeout = []
    try:
        new_image_data = [img for img in imgs.list()
                          if name in img.name and image in img.id]
    except:
        image.status == 'ERROR'

    for i in new_image_data:
        if i.status == 'ACTIVE' or not wait:
            success.append(i.id)
        elif i.status == 'ERROR':
            error.append(i.id)
        elif wait:
            timeout.append(i.id)

    results = {
        'changed': changed,
        'action': 'create',
        'image': image_name,
        'success': image_id,
        'error': error,
        'timeout': timeout,
    }

    if timeout:
        results['msg'] = 'Timeout waiting for image to build'
    elif error:
        results['msg'] = 'Failed to build an image'

    if 'msg' in results:
        module.fail_json(**results)
    else:
        module.exit_json(**results)


def main():
    argument_spec = rax_argument_spec()
    argument_spec.update(
        dict(
            name=dict(),
            id=dict(),
            image_name=dict(required=True),
            wait=dict(default=False, type='bool'),
            wait_timeout=dict(default=300),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=rax_required_together(),
        mutually_exclusive=[['name', 'id']],
        required_one_of=[['name', 'id']],
    )

    if not HAS_PYRAX:
        module.fail_json(msg='pyrax is required for this module')

    name = module.params.get('name')
    server_id = module.params.get('id')
    image_name = module.params.get('image_name')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    setup_rax_module(module, pyrax)

    rax_images(module, name, server_id, image_name, wait, wait_timeout)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.rax import *

### invoke the module
main()
