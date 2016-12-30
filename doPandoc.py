#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import errno
import subprocess
import os
import argparse
from subprocess import call

#
#	Use:
#	1 - Open cmd window in base directory:
#		* SHIFT-RightCLICK at the subject directory name in Explorer
#		* select 'Open cmd-window here'
#	2 - type: 'doPandoc --help' to get a full overview of its use
#
#
#	Include:
#		templates\<arg3>.[docx | tex]		(optional) the Word or Tex templates to be used by pandoc
#		src\mmd\<arg1>.mmd						This is the actual source mmd file
#		src\bib\<bibliography.bib>				(optional) your bib file, overrides as specified in the YAML-block
#		src\images							Here are the images stored that are used in the document
#		results\							This is directory where the generated result will be placed
#
#	Result: results\<arg1>.<arg2>
#


def InputError(msg, expr):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    print('ERROR: ' + msg + ': ' + expr + '\n')
    print('Type \'doPandoc -h\' for help\n')
    exit (1)
    return(0)

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = newPath

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def getGitUrl():
	from urllib.parse import urlparse
	# Ask the user for her Git server url
	# Return: the url of the git-server, or None if she wants to keep git local
	gitUrls = []
	gitUrls.append("http://gitlab.servicelab.org/plbt5/")
	gitUrls.append("https://git.ics.ele.tue.nl/pbrandt/")
	gitUrls.append("https://github.com/plbt5/")
	gitUrls.append(".... other (specify)")
	
	print("You don't have configured a git server yet. Select your git of choice:")
	for i, anUrl in enumerate(gitUrls):
		print("\t{}: {}".format(str(i), anUrl))
	my_url = ""
	while my_url == "":
		choice = input("Enter your number of choice, type your own git url, or <return> for None (i.e., keep git local): ")
		if len(choice) == 1 and (int(choice) >=0 and int(choice) < len(gitUrls)):
			my_url = gitUrls[int(choice)]
			print("Applying git server: {}".format(my_url))
		elif len(choice) > 7:
			u = urlparse(choice)
			if not u.scheme in ['http', 'https']:
				print("Can only accept 'http' or 'https' schemas")
			elif len(u.netloc.split('.')) < 1:
				print("Please use fully qualified network location (www.host.country_code)")
			else: 
				my_url = choice
				print("Applying git server: {}".format(my_url))
		elif len(choice) == 0: 
			my_url = None
			print("Applying local git only")
		else: 
			print("Can only accept a number, an url, or a single enter.")
	return my_url

		
def gitCommit(project=None, msg=None, major=None, minor=None):
	# Open shell and 
	# * Check for untracked textual assets and stage them
	# * commit changes
	# * tag Head with version
	# * push to remote
	assert project, "gitCommit(): Require project name, got None"
	assert msg, "gitCommit(): Require useful message, got None"
	
	remote_url = None
	retain_current = False
	
	# Check use of git, if not, initialise git
	try:
		result = subprocess.run(args=['git', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		result = subprocess.run(args=['git', 'remote', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		# A successful 'git remote -v' returns either (i) , or (ii) several paires of lines, formatted as <name> <url> [(fetch) | (push)] 
		if result.returncode == 0 and len(result.stdout) > 0:		
			remote_url = result.stdout.splitlines()[0].split()[1]
	except subprocess.CalledProcessError as e:
		assert "Not a git repository" in str(e.stderr), "gitCommit: unknown exception thrown, quitting ({})".format(str(e.stderr))
		print("You are not using git. Initializing git ...")
		try:
			result = subprocess.run(args=['git', 'init'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			major = minor = 0
			msg = "Project initiated in git, first commit"
			remote_url = getGitUrl()
			if remote_url:
				result = subprocess.run(args=['git', 'remote', 'add', 'origin', remote_url+'/'+project], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
				print("git result: {}".format(result))
		except subprocess.CalledProcessError as e:
			print("Error in 'git init' / 'git remote add origin': ({}) - git not used, hence no versioning".format(e.stdout))
			return
	# Stage (add) the changes to git
	try:
		scrivdir = project+'.scriv/Files/Docs/*.rtf'
		result = subprocess.run(args=['git', 'add', scrivdir], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		result = subprocess.run(args=['git', 'add', '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
	except subprocess.CalledProcessError as e: 
		print("git staging error: ({}) - maintaining current version ({}).".format(e.stderr, getVersion(True)))
		retain_current = True
		
	# Commit the changes to head, use commit message
	try:
		result = subprocess.run(args=['git', 'commit', '-m"'+msg+'"'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True)
	except subprocess.CalledProcessError as e: 
		retain_current = True
		if str(e.stdout).find("Your branch is up-to-date with", 0, 60):
			print("Branch is up-to-date, hence maintaining current version ({}).".format(getVersion(True)))
		else:
			print("git local commit error: ({})\nMaintaining current version ({}).".format(str(e.stderr), getVersion(True)))
		
	# On use of versioning, tag Head with version
	if not retain_current:
		tagGitHead(major, minor)

	if remote_url:
		# Push the local git commits to the remote repository
		try:
			result = subprocess.run(args=['git', 'push', '--follow-tags'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		except subprocess.CalledProcessError as e:
			# Push or commit returned error: GIT CANNOT ACCESS THE REMOTE REPOSITORY, 
			# assume (i) we are offline, and (ii) synchronisation will happen next time
			print("Warning: git commit/push error ({}).\nNot connected? Try next time".format(e.stderr))


def getVersion(concat = False):
	# Establish tag (=version), hash and commits on top of current version
	# return either concatenated version; or the three version parts major, minor, commits; or None if nothing found 
	try:
#		root = subprocess.check_output(['git', 'describe', '--tags', '--long', '--always']).decode('ascii').rstrip()	
		root = str(subprocess.run(args=['git', 'describe', '--tags', '--long', '--always'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True).stdout)
	except subprocess.CalledProcessError as e: 
		# Apparently git is not used
		print("git not used ({})".format(e.stderr))
		return None
	# Check whether our format is being used, i.e., x.y-z. If not, git is used but without tags
	if '-' in root.stdout:
		tag, commits, hash = root.split('-')
		major, minor = tag[1:].split('.')
	else: 
		tag = 'v0.0'
		commits = str(0)
	if concat:
		return tag + '-' + commits
	else:
		return int(major), int(minor), commits

def incrementVersion(level=None, concat = False):
	# Just return the incremented version, based on the requested level
	major, minor, commits = getVersion()
	if not commits:		# Apparently no git usage yet
		return None
	if level:
		if level == 'minor': 
			minor+=1
			commits = 0
		elif level == 'major':
			major += 1
			minor = 0
			commits = 0
		elif level == 'none': print("Retaining current version ({})".format(str(major) +'.'+ str(minor) +'-'+ str(commits)))
		else: 
			print('Incorrect versioning request: can only support "none" (default), "minor" or "major", got "{}"'.format(level))
			return None
	else:
		print("Retaining current version ({})".format(str(major) +'.'+ str(minor) +'-'+ str(commits)))
	if concat:
		return 'v' + str(major) + '.' + str(minor) + '-' + commits
	else:
		return int(major), int(minor), commits

def tagGitHead(major, minor):
	# Open shell and tag the current head
	print("tagging HEAD with v{}.{}".format(str(major),str(minor)))
	tag = 'v' + str(major) + '.' + str(minor)
	tagMsg = 'Version ' + tag
	try:
		result = subprocess.run(args=['git', 'tag', '-a', tag, '-m "'+tagMsg+'"'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True)
	except subprocess.CalledProcessError as e:
		print("git tagging error: {}".format(str(e.stderr)))



# debug: PRINT ARGUMENTS
# print ('arguments (', len(sys.argv), ') to this cmd are:: \n')
# print (str(sys.argv), flush=True)

# Set default template extensions for the various pandoc target formats
default = {}
default['docx'] = '.docx'
default['doc']  = '.doc'
default['tex']  = '.tex'
default['pdf']  = '.tex'
default['md']   = '.mmd'
default['mmd']  = '.mmd'
default['-d']   = 'templates'
default['-l']   = None
default['-g']   = None
default['-t']   = 'pandoc-docstyle'
default['-s']   = 'src'
default['-r']   = 'results'
default['-p']	= None

# Configure which pandoc extensions to include in the command
pandocExts = 'markdown_mmd'
pandocExts = pandocExts + '+auto_identifiers'
pandocExts = pandocExts + '+implicit_header_references'
pandocExts = pandocExts + '+yaml_metadata_block'
pandocExts = pandocExts + '+citations'
pandocExts = pandocExts + '+implicit_figures'
pandocExts = pandocExts + '+header_attributes'
pandocExts = pandocExts + '+pipe_tables'
pandocExts = pandocExts + '+grid_tables'
pandocExts = pandocExts + '+multiline_tables'
pandocExts = pandocExts + '+table_captions'
pandocExts = pandocExts + '+strikeout'
pandocExts = pandocExts + '+footnotes'
pandocExts = pandocExts + '+inline_notes'
pandocExts = pandocExts + '+tex_math_dollars'
pandocExts = pandocExts + '+superscript'
pandocExts = pandocExts + '+subscript'
pandocExts = pandocExts + '+raw_tex'
pandocExts = pandocExts + '+definition_lists'
pandocExts = pandocExts + '+fancy_lists'
pandocExts = pandocExts + '+example_lists'
pandocExts = pandocExts + '+startnum'
pandocExts = pandocExts + '+fenced_code_blocks'
pandocExts = pandocExts + '+fenced_code_attributes'
pandocExts = pandocExts + '+link_attributes'

# Get all arguments and ACK the command
parser = argparse.ArgumentParser(
    description='Wrapper around pandoc to spare lotsa typing!',
    epilog='''Besides the arguments above, any APPENDED arguments will be transferred 1-to-1 to pandoc, e.g., --toc. \n
            Execute this program by including the location of the program in the environment's PATH variable. \n
			All relative directories are relative to the current working directory of the shell.\n
            Make sure you include templates\ and src\ directories in the working directory.
			You can change these defaults by applying appropriate options.\n
            Regarding the expected structure of the project:
			* templates\ contains the template files to be used by pandoc, \n
            * src\ contains:\n
				- docs\ for your primary document source files (mmd or tex or docx or whatever), \n
				- bib\ for bib sources, \n
				- images\ for images used in your document. \n
            * results\ contains rhe result of the pandoc processing as: <source>.<format>\n
    '''
)
parser.add_argument('source', help='the name of the source file; leaving out the extension assumes .mmd')
parser.add_argument('format', choices=['doc', 'docx', 'tex', 'pdf'], help='the target format: [doc | docx | tex | pdf]')
parser.add_argument('-g', '--git', help='(optional) use git-versioning to commit the current text, tagged as new minor version. The text following this argument is considered the commit message (try to scale it to 50 chars). Only useful when you checked out your scrivener project from git', default=default['-g'])
parser.add_argument('-l', '--level', choices=['none', 'minor', 'major'], help='(optional) the version level that will be incremented (requires option -g <msg>, unless "-l")', default=default['-l'])
parser.add_argument('-t', '--template', help='(optional) your style template file; leaving out the extension implies compatibility with specified target format ', default=default['-t'])
parser.add_argument('-d', '--dDir', help='(optional) the root directory (relative to your project dir) holding the style template file ', default=default['-d'])
parser.add_argument('-s', '--sDir', help='(optional) the root directory (relative) holding the source document files ', default=default['-s'])
parser.add_argument('-r', '--rDir', help='(optional) the results directory (relative) holding the generated target file ', default=default['-r'])
parser.add_argument('-b', '--bib', help='(optional) your bib file, overriding what has been specified in the YAML-block; leaving out the extension assumes .bib')
parser.add_argument('-p', '--proj', help='(optional) the scrivener project(.scriv) directory holding the scrivener sources; assumes {} '.format(default['-p']), default=default['-p'])
args = parser.parse_known_args()

###########
# Process the arguments and assign parameters with proper values
###########
source = args[0].source
path,srcfile = os.path.split(source)
root,ext = os.path.splitext(srcfile)
if not ext:
	ext = '.mmd'
sourceFile = root + ext

gitMessage = args[0].git
targetDir = args[0].rDir
format = args[0].format
templateDir = args[0].dDir
project = args[0].proj
if path == os.path.join(args[0].sDir, "docs"):
	sourceDir = args[0].sDir
else: sourceDir = os.path.join(path, args[0].sDir)
baseDir = os.getcwd()	# The shell's current working directory
# Get the Scrivener project name, i.e., the name of the current working directory if no command argument has been given
cwd = baseDir.rsplit('\\', 1)
project = cwd[1] if not args[0].proj else args[0].proj
# Make exception for my dissertation:
if cwd[1] == "Dissertation": project = 'DissertatieBrandt'

mmdDir = os.path.join(sourceDir, "docs")
bibDir = os.path.join(sourceDir, "bib")
imgDir = os.path.join(sourceDir, "images")

root,ext = os.path.splitext(args[0].template)
if not ext:
	ext = default[args[0].format]
templateFile = root + ext

if args[0].bib:			# If it's not defined here, YAML-block data is assumed
	root,ext = os.path.splitext(args[0].bib)
	print ('head: <' + root + '>, tail: <' + ext + '>')
	if not ext:
		ext = '.bib'
	bibFile = root + ext

targetFile = os.path.splitext(sourceFile)[0] + '.' + format

###########
# Consider the use of versioning, i.e., calculate potential new version. Note that the option '-l' demands '-g'
###########
version = ''
if gitMessage:
	# IF there is a Git message, then the default level will be 'minor'
	level = args[0].level if args[0].level else 'minor'
	version = incrementVersion(level, True)
elif (args[0].level and args[0].level == 'none') or not args[0].level:
	# If there is NO git message, then we will generate one if the purpose is retain the same version number
	gitMessage='(auto message) Small textual changes only'
	version = getVersion(True)
else:
	# If the purpose is to increment the version number, but do so WITHOUT git message, that's not good 
	# (this should have been captured by the earlier command line option processing; this is for fail-safe only)
	print("ERROR: Will not create a new version without a proper commit message; '-l' demands '-g <msg>'")
	exit()
	
# if args[0].level and gitMessage and args[0].level in ['major', 'minor', 'none']:
	# assert len(gitMessage) > 1, "Will not create a new version without a proper commit message; '-l' demands '-g <msg>'"
# #	version = gitCommit(project=project, msg=gitMessage, versionLevel=args[0].level)
# elif gitMessage:
	# assert len(gitMessage) > 1, "Will not commit without a proper commit message; either use '-g <msg>' or don't use '-g'"
	# # Since a git message is present, and no correct level has been given, enforce increment of minor version
# #	version = gitCommit(project=project, msg=gitMessage, versionLevel='minor')
	# version = incrementVersion(level='minor', True)
# elif args[0].level == 'none':
# #	version = None
	# version = getVersion(True)
# else: 
	# # Commit the current status, but maintain the current version. This commit is distinguishable by its increment of the total commits only
	# version = gitCommit(project=project, msg='(auto message) Small textual changes only')

###########
# Present relevant parameter details
###########
print ('base directory is    :' + baseDir)
print ('template directory is:' + templateDir)
print ('source file is       :' + sourceFile)
print ('target file is       :' + targetFile)
print ('template file is     :' + os.path.join(templateDir,templateFile))
print ('version is           :' + (version if version else ''))

###########
# Check existence of main files
###########
if not os.path.exists(os.path.join(baseDir, mmdDir, sourceFile)): 
    print('source file not found', os.path.join(baseDir, mmdDir, sourceFile))
    print('searching subfolder ...')
    # Especially with scrivener mmd projects, an additional compile folder may be introduced
    if not os.path.exists(os.path.join(baseDir, mmdDir, sourceFile, sourceFile)): 
        InputError('source file not found', os.path.join(baseDir, mmdDir, sourceFile, sourceFile))
    else: 
        src_filename = os.path.join(mmdDir, sourceFile, sourceFile)
else: 
    src_filename = os.path.join(mmdDir, sourceFile)
if not os.path.exists(os.path.join(baseDir, templateDir, templateFile)): InputError('template file not found', os.path.join(baseDir, templateDir, templateFile))

###########
# Parse and build the arguments for pandoc
###########

pandoc_args = {}
pandoc_args['-f'] = pandocExts
pandoc_args['-o'] = os.path.join(targetDir,targetFile)
print ('output to            :' + pandoc_args['-o'])
pandoc_args['--data-dir'] = baseDir
pandoc_args['--filter'] = 'pandoc-citeproc'				# Using an external filter, pandoc-citeproc, pandoc can automatically generate citations and a bibliography in a number of styles
if args[0].bib:                                 		# Bibliography file given as argument that overrides YAML block
    pandoc_args['--bibliography'] = os.path.join(bibDir, bibFile) 
pandoc_bools = ["--number-sections"]          			# ".. as seen in section 2.1.3" You can configure (1) which symbol to use (num-sign by default), and (2) whether to link back to the referred section, or convert the link to plain text (link by default)
pandoc_bools.append("--top-level-division=chapter")		# Treat mmd top-level headers as chapters 
pandoc_bools.append("--smart")							# Produce typographically correct output, converting straight quotes to curly quotes, --- to em-dashes, -- to en-dashes, and ... to ellipses, etc.
if version:
	pandoc_args['-M'] = 'version=' + version 			# Pass the version for this document as meta-data to be used in the template
if (format == "docx"):
	pandoc_args['--reference-docx'] = os.path.join(templateDir,templateFile)
else:
	pandoc_args['--template'] = os.path.join(templateDir,templateFile)

pArgs = [ 'pandoc' ]
for key in ('-o', '-f'): 
    pArgs.extend([key,pandoc_args[key]])
    del pandoc_args[key]

for key,val in pandoc_args.items():
	pArgs.extend([key,val])

pArgs.extend(pandoc_bools)

# Add non-parsed, additional arguments from the command line, if any
for val in args[1]:
	pArgs.append(val)

# Append the mmd source    
pArgs.append(src_filename)

###########
# Run pandoc
###########

with cd(baseDir):
	print ('changed dir to: '+ os.getcwd())
	print ('Running \n{}\n'.format(str(pArgs)))

	rc = subprocess.call(pArgs)                 # Do the actual pandoc operation and safe its return value

	if (rc == 0):                               # When pandoc didn't complain, we can stage, commit and sync the docs to git, and finally open the resulting file
		# TODO: INCORRECT CODING: This is not completely correct. In the event git establishes that current branch is up-to-date, it will not increase the version number (only hash update). 
		# However, the document has been generated with the newly calculated version number already. Therefore, we need to modify the process and first commit, then pandoc, and, if pandoc
		# complains, replace the local changes (i.e., checkout previous version)
		if version and not version == 'v0.0-0': 
			major, minor = version[1:].split('-')[0].split('.')
		else:
			major = minor = None
		gitCommit(project=project, msg=gitMessage, major=major, minor=minor)
		os.startfile(os.path.join(targetDir,targetFile), 'open')
	else: print("\n>>>> ERROR: pandoc returned with {}".format(rc))
	


print ('Done!\n')



