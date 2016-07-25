#!/usr/bin/python3
import subprocess
import requests
import argparse
import hashlib
import json
import glob
import os


def validate_file(file, digest=None):
    """ Validate the integrity of the given file

    Args:
        file: File to validate
        digest: Expected SHA256 checksum of the file

    Raises: ValueError
    """
    file_digest = hashlib.sha256(file).hexdigest()
    if digest:
        # Validate file integrity
        if file_digest != digest:
            raise ValueError('file digest mismatch: ' + file_digest + ' != ' + digest)
    else:
        # If no digest is specified, print it so it can be added to the mod specification
        print('\t\t' + file_digest)


def generate_mod_filename(spec):
    """ Use the mod specification to generate a filename

    format: [name-[version-]]tag.jar

    Args:
        spec: Mod specification

    Returns: Path for the saved mod file
    """
    # Generate tag from hashed source URL
    if spec.get('source'):
        tag = hashlib.sha256(spec['source'].encode('utf-8')).hexdigest()[:6]
    else:
        # No source URL - use placeholder
        tag = '<stub>'
    name = spec.get('name', tag)
    version = spec.get('version', None)
    if name is not tag:
        name += ('-' + version + '-' if version else '-') + tag
    return name + '.jar'


def download_file(source, destination, digest=None):
    """ Download the remote file, verify its integrity, and save it to the destination

    Args:
        source: URL to download the file
        destination: Path for the saved file
        digest: SHA256 file checksum
    """
    # Placeholder entry (no source URL) - skip
    if not source:
        print('\t[-] ' + destination)
        return

    # File already exists - validate against given digest
    if os.path.exists(destination):
        with open(destination, 'rb') as file:
            validate_file(file.read(), digest)
        print('\t[o] ' + destination)

    # Download new file from source URL
    else:
        r = requests.get(source)
        validate_file(r.content, digest)
        with open(destination, 'wb') as file:
            file.write(r.content)
        print('\t[\u2713] ' + destination)

###########################################################
#                       BEGIN PROGRAM                     #
###########################################################

parser = argparse.ArgumentParser(description='Import files for a modpack')
parser.add_argument('spec', help='Modpack JSON specification')
group = parser.add_mutually_exclusive_group()
group.add_argument('-s', '--server', action='store_true', help='Install the Forge server files')
group.add_argument('-c', '--client', action='store_true', help='Download the Forge installer')
arguments = parser.parse_args()

# TODO: Add JSON schema validation and formatting help
# TODO: Remove mods that are not in the specification
# TODO: Allow mods to be client-only or server-only

# Load modpack data from JSON
print('Loading modpack configuration')
with open(arguments.spec) as config:
    modpack = json.load(config)
print('Forge version: ' + modpack['forge'].get('version', '<unknown>'))

# Initialize mods directory
if not os.path.exists('mods'):
    os.mkdir('mods')

# Download the mod files
print('Importing ' + str(len(modpack['mods'])) + ' mods:')
for mod in modpack['mods']:
    download_file(mod['source'], os.path.join('mods', generate_mod_filename(mod)), mod.get('digest'))

print(arguments)
# Download the Forge installer
if arguments.server or arguments.client:
        print('Retrieving installer for Forge:')
        download_file(modpack['forge']['source'], 'forge-installer.jar', modpack['forge'].get('digest'))

        # Install the Forge server files
        if arguments.server:
            print('Installing Forge server files')
            subprocess.call(['java', '-jar', 'forge-installer.jar', '--installServer'], stdout=open(os.devnull))
            os.rename(glob.glob('forge-*-universal.jar')[0], 'forge-server.jar')
print('Modpack imported')
