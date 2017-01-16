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

class Git:
	# represents the handle to the operating system calls to address any git command for this.

	def __init__(self, project=None):
		assert project, "Git requires a project name, got none"
		self.project = project
		# Check use of git, if not, initialise git
		try:
			result = subprocess.run(args=['git', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		except subprocess.CalledProcessError as e:
			assert "Not a git repository" in str(e.stderr), "gitCommit: unknown exception thrown, quitting ({})".format(str(e.stderr))
			self.init()
	
	def init(self):
		print("* ** Initializing local git ...")
		try:
			result = subprocess.run(args=['git', 'init'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		except subprocess.CalledProcessError as e:
			raise NotImplementedError("Error initializing git: ({}) - git not used, hence no versioning".format(e.stdout))
		# Do first commit
		major = minor = 0
		msg = "Project initiated in git, first commit"
		self.commit(msg=msg, major=major, minor=minor)
		# Push to remote
		self.push()
		
	def getUrl(self):
		# Assess whether a git server has been configured.
		# Return: the url of the configured git server, or None if not configured
		if not hasattr(self, 'remote_url'):
			try:
				result = subprocess.run(args=['git', 'remote', 'get-url', 'origin'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True).stdout.decode('ascii').rstrip()
				self.remote_url = result
			except subprocess.CalledProcessError as e:
				assert ("Not a git repository" in str(e.stderr)) or ("No such remote 'origin'" in str(e.stderr)), "gitCommit: unknown exception thrown, quitting ({})".format(str(e.stderr))
				return None
		return self.remote_url

	def askUrl(self): 
		# Ask the user for her Git server url
		# Return: the url of the git-server, or None if she wants to keep git local
		# Note: this will overwrite any self.remote_url
		from urllib.parse import urlparse
		gitUrls = []
		gitUrls.append("http://gitlab.servicelab.org/plbt5/")
		gitUrls.append("https://git.ics.ele.tue.nl/pbrandt/")
		gitUrls.append("https://github.com/plbt5/")
		gitUrls.append(".... other (specify)")
		
		# Check that there is no remote git server already
		my_url = self.getUrl()
		if my_url: return my_url
		print("* ** Consider to configure a remote server for this local git.")
		choice = ''
		while not choice in ['s', 'S', 'c', 'C']:
			choice = input("Remote Git Server: already [c]reated your project remotely, or [s]kip configuring a remote server for this local git? [s]") or "s"
		if choice.lower() == 's': return None
		for i, anUrl in enumerate(gitUrls):
			print("* ** \t{}: {}".format(str(i), anUrl))
		my_url = ""
		while my_url == "":
			choice = input("Enter your number of choice, or <return> for None (i.e., keep git local): ")
			if len(choice) == 1 and int(choice) >=0 and int(choice) < len(gitUrls)-1:
				my_url = gitUrls[int(choice)]
				print("* ** Applying git server: {}".format(my_url))
			elif int(choice) == len(gitUrls):
				url_spec = urlparse(input("Enter the (fully qualified domain name) url of the git server, including your account: "))
				if not url_spec.scheme in ['http', 'https']:
					print("* ** Can only accept 'http' or 'https' schemas")
				elif len(url_spec.netloc.split('.')) < 1:
					print("* ** Please use fully qualified network location (www.host.country_code)")
				else: 
					my_url = url_spec.geturl()
					print("* ** Applying git server: {}".format(my_url))
			elif len(choice) == 0: 
				my_url = None
				print("* ** Applying local git only")
			else: 
				print("* ** Can only accept a number, or a single enter.")
		self.remote_url = my_url
		return my_url
			
	def commit(self, msg=None, major=None, minor=None):
		# Open shell and 
		# * Check for untracked textual assets and stage them
		# * commit changes
		# * tag Head with version
		# * do not yet push to remote; this because the commit can contain errors that we do not want to push to the remote
		assert msg, "gitCommit(): Require useful message, got None"
		
		# Stage (add) the changes to git
		try:
			result = subprocess.run(args=['git', 'add', self.project+'.scriv/Files/Docs/*.rtf'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			result = subprocess.run(args=['git', 'add', self.project+'.scriv/Settings/*'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			result = subprocess.run(args=['git', 'add', self.project+'.scriv/Snapshots/*'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			result = subprocess.run(args=['git', 'add', 'src/*'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			result = subprocess.run(args=['git', 'add', 'templates/*'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			result = subprocess.run(args=['git', 'add', '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
		except subprocess.CalledProcessError as e: 
			print("* git staging error: ({}) - maintaining current version ({}).".format(e.stderr, self.version(True)))
			return
			
		# Commit the changes to head, use commit message
		try:
			result = subprocess.run(args=['git', 'commit', '-m"'+msg+'"'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True)
		except subprocess.CalledProcessError as e: 
			if str(e.stdout).find("Your branch is up-to-date with", 0, 60):
				print("* Branch is up-to-date, hence maintaining current version and same commit ({}).".format(self.version(True)))
				return
			else:
				print("WARNING: git local commit error: ({})\nMaintaining current version and same commit ({}).".format(str(e.stderr), self.version(True)))
				return
		# On use of versioning (i.e. major and minor have an actual value) and new version is eminent, tag Head with version
		if major and minor:
			self.tagHead(major, minor)
		return
		

	def push(self):
		# Push the local git commits to the remote repository
		# return: True on success, False when not pushed (deliberately or on fault)
		if not self.getUrl():
			# No remote repository yet, create one
			remote_url = self.askUrl()
			if remote_url:
				# The remote server was just introduced, hence add origin to remote
				try:
					result = subprocess.run(args=['git', 'remote', 'add', 'origin', remote_url+'/'+project], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
					result = subprocess.run(args=['git', 'push', '--set-upstream', 'origin',  'master'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
				except subprocess.CalledProcessError as e:
					print("* git: cannot add origin to remote, or add upstream (tracking) reference ({}) - remote git not used".format(e.stdout))
					# Clear the remote url reference and return false
					self.remote_url = None
					return False
			else:
				# User chose local git only
				return False
		# Here, a new remote server may just have been setup. Or, we already had a remote server. Then, do the actual push.
		if self.getUrl():
			print("* pushing commit to server ({})".format(self.getUrl()))
			try:
				result = subprocess.run(args=['git', 'push', '--follow-tags'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
				return True
			except subprocess.CalledProcessError as e:
				if str(e.stderr).find("fatal: The current branch '"+self.getBranches()['current']+"' has no upstream branch"):
					result = subprocess.run(args=['git', 'push', '--set-upstream', 'origin', self.getBranches()['current']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
				else:
					# Push returned error: GIT CANNOT ACCESS THE REMOTE REPOSITORY, aither because it has not yet been 
					# assume (i) we are offline, and (ii) synchronisation will happen next time
					print("* Warning: git push error ({}).\nNot connected? Try next time".format(e.stderr))
		return False

	def version(self, concat = False):
		# Establish tag (=version), hash and commits on top of current version
		# return either concatenated version; or the three version parts major, minor, commits; or None if git not found 
		# Note: when no versioning is found, our versioning scheme 'v<major>.<minor>-<commits>' will be introduced
		try:
			root = subprocess.run(args=['git', 'describe', '--tags', '--long', '--always'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True).stdout.decode('ascii').rstrip()
		except subprocess.CalledProcessError as e: 
			# Apparently git is not used
			print("* git not used ({})".format(e.stderr))
			return None if concat else None, None, None
		# Check whether our format is being used, i.e., x.y-z. If not, git is used but without our versioning scheme
		if '-' in str(root):
			tag, commits, hash = root.split('-')
			major, minor = tag[1:].split('.')
		else: 
			# Enforce our versioning scheme by initializing it with v0.0-curr_commits
			tag = 'v0.0'
			major = minor = '0'
			commits = subprocess.run(args=['git', 'rev-list', 'HEAD', '--count'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True).stdout.decode('ascii').rstrip()
			print("* ** init versioning ({})".format(self.tagHead(major, minor)))
		if concat:
			return tag + '-' + commits
		else:
			return int(major), int(minor), int(commits)

	def incrementVersion(self, level=None, concat = False):
		# Just return the incremented version, based on the requested level
		major, minor, commits = self.version()
		if not commits:		# Apparently no git usage yet
			return None
		if level:
			if level == 'minor': 
				minor+=1
			elif level == 'major':
				major += 1
				minor = 0
			elif level == 'none': 
				pass
				# print("Retaining current version ({}) but increment current commit number ({})".format(str(major) +'.'+ str(minor), str(commits)))
			else: 
				print('* Warning: Incorrect versioning request: can only support "none" (default), "minor" or "major", got "{}"'.format(level))
				return None
		else:
			#print("Retaining current version ({}) but increment current commit number ({})".format(str(major) +'.'+ str(minor), str(commits)))
			pass
		if concat:
			return 'v' + str(major) + '.' + str(minor) + '-' + str(commits)
		else:
			return int(major), int(minor), int(commits)

	def tagHead(self, major, minor):
		# Open shell and tag the current head
		# return: 'v<major>.<minor>' if successful, None otherwise
		tag = 'v' + str(major) + '.' + str(minor)
		tagMsg = 'Version ' + tag
		try:
			result = subprocess.run(args=['git', 'tag', '-a', tag, '-m "'+tagMsg+'"'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
			return result
		except subprocess.CalledProcessError as e:
			if str(e.stdout).find("fatal: tag '"+tag+"' already exists", 0, 40):
				return tag
			else: 
				print("* Warning: got Git tagging error: {}".format(str(e.stderr)))
				return None
				
	def getBranches(self):
		# Return the current branch
		if not hasattr(self, 'branches'):
			self.branches = {}
			# Assume no issues to result from this call. If it does, we probably want to abort anyway. Make further distinction to errors through Try/Except if required.
			result = subprocess.run(args=['git', 'branch'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
			for br in result.splitlines():
				if br[0] == '*': 
					self.branches['current']=br[2:]
#					print("debug: * ({})".format(self.branches['current']))
				else: 
					self.branches[br[2:]]=br[2:]
#					print("debug:   ({})".format(self.branches[br[2:]]))
		return self.branches

	def addBranch(self, branch, current=False):
		if not hasattr(self, 'branches'): 
			self.branches = {}
		self.branches[branch]=branch
		if current: self.setCurrentBranch(branch)
	
	def setCurrentBranch(self,branch=None):
		assert hasattr(self, 'branches'), "setCurrentBranch(): cannot set current branch if no branch exist yet"
		assert branch, "setCurrentBranch(): branch name required, got none"
		temp = self.branches['current']
		self.branches['current'] = branch
		self.branches[temp] = temp
		
	def getStatus(self):
		# Return the current branch
		if not hasattr(self, 'status'):
			# Assume no issues to result from this call. If it does, we probably want to abort anyway. Make further distinction to errors through Try/Except if required.
			results = subprocess.run(args=['git', 'status'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
			# The second line provides the requested information
			lines = results.splitlines()
			self.status = lines[1]
#			print("debug: status is ({})".format(self.status))
		return self.status
			
	def checkout(self, branch=None):
		# Change, in a safe way, to the requested branch. Create the branch if it does not exist yet.
		# Return the name of the current branch
		# First, establish whether we are already on the requested branch
		if branch == self.getBranches()['current']: return branch
		# We are on another branch, hence
		# 1 - save the current work in this branch, i.e., stage and commit
		self.commit(msg="saving work from current branch {} before checking out branch {}".format(self.getBranches()['current'], branch))
		# 2 - check whether the branch exists
		if not branch in list(self.getBranches().values()): 
			# Branch doesn't exist hence create it:
			# 2.1 - make sure to sit on the master, since we want that to be its parent
			if self.getBranches()['current'] != "master":
				# 2.1a - Change to master branch
				try:
					result = subprocess.run(args=['git', 'checkout', 'master'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
				except subprocess.CalledProcessError as e:
					raise NotImplementedError("checkout(): git checkout 'master' returned error: {}".format(str(e.stderr))) 
				# 2.1b - pull the master since we want to branch from the latest commit at the master
				result = subprocess.run(args=['git', 'pull'], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
			# 2.2 - create the branch, and update the object with its name
			result = subprocess.run(args=['git', 'checkout', '-b', branch], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
			# 2.3 - update the object with its name
			self.addBranch(branch, True)
			# 2.4 - push the new branch to remote
#			print("debug: git push --set-upstream origin {}".format(branch))
			result = subprocess.run(args=['git', 'push', '--set-upstream', 'origin', branch], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
			return branch
		# 3 - branch exists, so just change to it
		result = subprocess.run(args=['git', 'checkout', branch], stdin=None, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=None, check=True).stdout.decode('ascii').rstrip()
		if "Switched to branch" in result.rsplit(maxsplit=1):
			# and set the object to the correct current
			self.setCurrentBranch(result.rsplit(maxsplit=1))
			return result.rsplit(maxsplit=1)[1]
		else:
			raise NotImplementedError("checkout(): git returned unexpected string during checkout of ({}): {}".format(branch, result)) 



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
default['-c']   = 'master'

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
			\n
			When this project is under git control, it will manage your versions and branches for you in a specific scenario: \n
			1. to be added
    '''
)
parser.add_argument('source', help='the name of the source file; leaving out the extension assumes .mmd')
parser.add_argument('format', choices=['doc', 'docx', 'tex', 'pdf'], help='the target format: [doc | docx | tex | pdf]')
parser.add_argument('-g', '--git', help='(optional) use git-versioning to commit the current text, tagged as new minor version. The text following this argument is considered the commit message (try to scale it to 50 chars). Only useful when you checked out your scrivener project from git', default=default['-g'])
parser.add_argument('-l', '--level', choices=['none', 'minor', 'major'], help='(optional) the version level that will be incremented (requires option -g <msg>, unless "-l")', default=default['-l'])
parser.add_argument('-c', '--checkout', help='(optional) checkout to this branch (overrides the "category" parameter in the documents YAML-block) ', default=default['-c'])
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
# Get the Scrivener project name, i.e., the name of the current working directory (no path) if no command argument has been given
dirname = baseDir.rsplit('\\', 1)
project = dirname[1] if not args[0].proj else args[0].proj
# Make exception for my dissertation:
if dirname[1] == "Dissertation": project = 'DissertatieBrandt'

mmdDir = os.path.join(sourceDir, "docs")
bibDir = os.path.join(sourceDir, "bib")
imgDir = os.path.join(sourceDir, "images")

root,ext = os.path.splitext(args[0].template)
if not ext:
	ext = default[args[0].format]
templateFile = root + ext

if args[0].bib:			# If it's not defined here, YAML-block data is assumed
	root,ext = os.path.splitext(args[0].bib)
	print ('debug: bib file name: <' + root + '>, extension: <' + ext + '>')
	if not ext:
		ext = '.bib'
	bibFile = root + ext

targetFile = os.path.splitext(sourceFile)[0] + '.' + format


###########
# Present relevant parameter details
###########
print ('**********************')
print('*')
print ('* Processing project <' + project + '>:')
print ('* base directory is    : ' + baseDir)
print ('* template directory is: ' + templateDir)
print ('* source file is       : ' + sourceFile)
print ('* target file is       : ' + targetFile)
print ('* template file is     : ' + os.path.join(templateDir,templateFile))


###########
# Check existence of main files
###########
if not os.path.exists(os.path.join(baseDir, mmdDir, sourceFile)): 
    print('* Warning: source file not found', os.path.join(baseDir, mmdDir, sourceFile))
    print('*\tsearching subfolder ...')
    # Especially with scrivener mmd projects, an additional compile folder may be introduced
    if not os.path.exists(os.path.join(baseDir, mmdDir, sourceFile, sourceFile)): 
        InputError('source file not found', os.path.join(baseDir, mmdDir, sourceFile, sourceFile))
    else: 
        src_filename = os.path.join(mmdDir, sourceFile, sourceFile)
else: 
    src_filename = os.path.join(mmdDir, sourceFile)
if not os.path.exists(os.path.join(baseDir, templateDir, templateFile)): InputError('template file not found', os.path.join(baseDir, templateDir, templateFile))

###########
# Establish the branch we are working on
###########

# Skip branching with the undocmented command option -c 0
if args[0] != 0:
	default_branch='master'
	if sourceFile.split('.')[-1] == 'mmd':
		# Parse the multimarkdown file for a YAML block containing the "category: <my category>" line
		# unless there was an argument to the doPandoc to this concern
		# On failure, the branch name becomes 'master'
		if args[0].checkout == default_branch:
			# No argument given, hence parse the YAML block
			with open(src_filename, 'r') as f:
				line = f.readline()
				if line.find("---") == -1: 
					# no YAML block found
					branch = args[0].checkout
				else:
					# First line is YAML block
					for line in f:
						if line.lower().find("category") == -1 and line.find("...") == -1: continue
						if line.find("...") != -1: 
							# End of YAML block found
							branch = args[0].checkout
							break
						else:
							# Line "category: <my particular category name> parameter found
							branch = line.rsplit(sep=":", maxsplit=1)[1].strip("' \n")
							break
		else: branch = args[0].checkout
	else: branch = args[0].checkout

###########
# Consider the use of versioning, i.e., calculate potential new version. Note that the option '-l' demands '-g'
###########
version = ''
myGit = Git(project)
print ('* git branch is        : {}'.format(myGit.checkout(branch) if args[0].checkout != 0 else '-skipped-' ))
if gitMessage:
	# If there is a Git message, then the default level will be 'minor'
	level = args[0].level if args[0].level else 'minor'
	version = myGit.incrementVersion(level=level, concat=True)
elif (args[0].level and args[0].level == 'none') or not args[0].level:
	# If there is NO git message, and also no level or 'none' level then this is an update to the text that is not worth a level increment
	# Hence, we will generate a default git message, retain the same version number but increment the commit number
	gitMessage='(auto message) Small textual changes only'
	version = myGit.incrementVersion(level=None, concat=True)
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
# Stage, commit and push your modifications
###########
with cd(baseDir):
	if version and not version == 'v0.0-0': 
		major, minor = version[1:].split('-')[0].split('.')
	else:
		major = minor = None
	myGit.commit(msg=gitMessage, major=major, minor=minor)

print ('* version is           : ' + (version if version else ''))

###########
# Parse and build the arguments for pandoc
###########

pandoc_args = {}
pandoc_args['-f'] = pandocExts
pandoc_args['-o'] = os.path.join(targetDir,targetFile)
print ('* output to            : ' + pandoc_args['-o'])
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
	print ('* Running \n{}\n'.format(str(pArgs)))

	rc = subprocess.call(pArgs)                 # Do the actual pandoc operation and safe its return value

	if (rc == 0):                               # When pandoc didn't complain, we can push the current documents to git, and finally open the resulting file
		# if version and not version == 'v0.0-0': 
			# major, minor = version[1:].split('-')[0].split('.')
		# else:
			# major = minor = None
		# gitCommit(project=project, msg=gitMessage, major=major, minor=minor)
		
		# pandoc ran perfectly, hence no issues in its sources. Hence we can push the sources to the server, if any
		_ = myGit.push()
		os.startfile(os.path.join(targetDir,targetFile), 'open')
	else: 
		# pandoc ran into problems. Hence, no result was delivered and therefore the source documents contain errors. Do a roll-back on git to the original state.
		print("\n>>>> ERROR: pandoc returned with {}".format(rc))
		
	


print ('* Done!')
print('*')
print ('**********************\n')



