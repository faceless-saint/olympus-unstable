#!/usr/bin/python3
import subprocess
import requests
import argparse
import hashlib
import json
import glob
import os

# TODO: Allow for user selection of checksum algorithm (currently using SHA256)


def parse_arguments():
    """ Parse command line arguments for the program

    Returns: Parsed argument namespace
    """
    parser = argparse.ArgumentParser(
        description='Import files for the given modpack configuration',
        epilog=''' schema: {
            forge: {
                source: '<URL>',
                version: '[str]'
            },
            mods: [
                {
                    source: '<URL>',
                    name: '[str]',
                    version: '[str]',
                    disabled: [bool=false]
                },
                ...
            ]
        }''')
    parser.add_argument('spec', metavar='FILE', help='modpack JSON specification')
    parser.add_argument('target', metavar='DIR', nargs='?', default=os.getcwd(), help='import files to this directory')
    parser.add_argument('-p', '--preserve', action='store_true', help='skip removal of obsolete mods')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s', '--server', action='store_true', help='import the modpack for a server')
    group.add_argument('-c', '--client', action='store_true', help='import the modpack for a standalone client')
    return parser.parse_args()


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
    return name + ('.jar' if not spec.get('disabled') else '.jar.disabled')


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
        print('\t[o] ' + destination)
        with open(destination, 'rb') as file:
            validate_file(file.read(), digest)

    # Download new file from source URL
    else:
        print('\t[\u2193] ' + destination)
        try:
            r = requests.get(source)
            validate_file(r.content, digest)
            with open(destination, 'wb') as file:
                file.write(r.content)
        except requests.HTTPError as e:
            print('\t[x] ' + destination)
            raise e


###########################################################
#                       BEGIN PROGRAM                     #
###########################################################
arguments = parse_arguments()

# Load modpack data from JSON
print('Loading modpack configuration from ' + arguments.spec)
with open(arguments.spec) as config:
    modpack = json.load(config)
os.chdir(arguments.target)
print('Forge version: ' + modpack.get('forge', {}).get('version', '<unknown>'))

# Initialize mods directory
if not os.path.exists('mods'):
    os.mkdir('mods')

# Only import server mods
if arguments.server:
    mods = [mod for mod in modpack.get('mods', []) if not mod.get('client')]

# Only import client mods
else:
    mods = [mod for mod in modpack.get('mods', []) if not mod.get('server')]

# Prune the mod directory of obsolete files
if not arguments.preserve:
    for mod in os.listdir('mods'):
        if mod not in [generate_mod_filename(el) for el in mods] and not os.path.isdir(os.path.join('mods', mod)):
            os.remove(os.path.join('mods', mod))

# Download the mod files
print('Importing ' + str(len(mods)) + ' mods:')
for mod in mods:
    download_file(mod.get('source'), os.path.join('mods', generate_mod_filename(mod)), mod.get('digest'))

# Download the Forge installer
if arguments.server or arguments.client:
        forge = modpack.get('forge', {})
        print('Retrieving installer for Minecraft Forge:')
        download_file(forge.get('source'), 'forge-installer.jar', forge.get('digest'))

        # Install the Forge server files
        if arguments.server and os.path.exists('forge-installer.jar'):
            print('Installing Minecraft Forge server files')
            subprocess.call(['java', '-jar', 'forge-installer.jar', '--installServer'], stdout=open(os.devnull))
            os.rename(glob.glob('forge-*-universal.jar')[0], 'forge-server.jar')
print('Modpack imported')
