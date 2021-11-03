import os
import re
import docker
from coolname import generate_slug


def inputcheck(words):
	"""
	This is to sanitize user input.
	This removes anything that does not match the regex
	Only a-z A-z 0-9 - _ allowed
	"""
	pattern = r'[^a-zA-Z0-9-_]'
	clean_word = [re.sub(pattern, '', word) for word in words]
	return clean_word


class GetImages:
	"""
	This class has the methods and attributes to get the
	images of a user.
	"""

	def __init__(self, username, parent_dir):
		self.username = username
		self.parent_dir = parent_dir
		self.imgs = "*Your images:*\n"

	def get_images(self):
		"""
		This gets all the Dockerfile names, i.e all images and
		stores them in a dictionary and uses a counter variable as the key.
		"""

	# Need to improve.
	# Checking for the images this way is not good as sometimes the Dockerfile might
	# get created but not the image itself. So it's better to get the list of images from the repo.
	# Should figure out if there's any better way to do the same

		ctr = 1
		try:
			for file in os.listdir(self.parent_dir + "/" + self.username):
				self.imgs = self.imgs + str(ctr) + ". " + file + "\n"
				ctr = ctr + 1
			return self.imgs
		except FileNotFoundError:
			self.imgs = "No images. Use \"/build\" to start building an image."

	def get_info(self):
		"""
		This gives additional info on a particular image.
		"""
		pass


class CreateDockerfile:

	def __init__(self, username, tools, parent_dir):
		self.username = username
		self.tools = tools
		self.status = "not built"
		self.dockerfile_name = generate_slug(2)
		self.dest_file = ""
		self.parent_dir = parent_dir

	def fileparse(self):
		"""
		This method creates the installation Dockerfile instruction, replaces
		"TEMP" with the created instruction and stores the contents of the
		new Dockerfile in a variable.
		This also creates the file name of the Dockerfile from the tools list.
		"""
		sourcefile = "Dockerfile"
		tools_list = self.tools.split(",")

		run_instr = " ".join(["&& apt-get install -y " + tool for tool in tools_list])
		modified_run = open(sourcefile).read().replace("TEMP", run_instr)
		self.dest_file = self.parent_dir + "/" + self.username + "/" + self.dockerfile_name  # Destination Dockerfile path

		self.checkit(modified_run)


	def checkit(self, modified_run):
		"""
		This method checks if the user's dir and dockerfile are already present.
		If so, it skips dockerfile creation.
		"""

	# Should improve. See if we can compare the SHA hashes or the layers of the images
	# to check if the image we are building already exists. But that needs the image to built.
	# Best way as of now is to check for the list of tools of each image from the db (after setting up db)

		dir = self.parent_dir + self.username  # self.dest_file.split("/")[1]

		if not os.path.isdir(dir):
			os.mkdir(dir)
			self.writefile(modified_run)
		else:
			if os.path.isfile(self.dest_file):
				self.status = "File already there"
				self.dockerfile_name = ""  # setting to empty as we dont want the name to be returned if writefile is not called
			else:
				self.writefile(modified_run)

	def writefile(self, modified_run):
		"""
		This method writes the updated content stored in a varible by the
		fileparse() method to a new dockerfile.
		"""
		with open(self.dest_file, "w") as f:
			f.write(modified_run)

		self.status = "built"


class ManageImage:

	def __init__(self, username, tools, image_name, parent_dir, dest_file):
		self.username = username
		self.tools = tools
		self.parent_dir = parent_dir
		self.dest_file = dest_file
		self.status = ""
		self.image_name = image_name
		self.pull_link = "everythingtogold/gold:" + self.image_name

	def buildpush(self):
		"""
		This method builds, tags and pushes the image.
		"""
		dockerfile_path = self.parent_dir + "/" + self.username

		client = docker.from_env()
		print(client.login("everythingtogold", "bfaaufr@gurumail.xyZ", "tannor.dashon@icelogs.com"))

		try:
			print(client.images.build(path=dockerfile_path, dockerfile=self.image_name, tag=self.pull_link, rm=True))
		except docker.errors.BuildError as e:
			self.pull_link = ""
			self.status = str(e)

		client.images.push(repository="everythingtogold/gold", tag=self.image_name)
		self.status

	def remove_images(self):
		pass


###################################################
# Classes and their methods that should be added:
#   class container:
#    def start()
#    def stop()
#    def exec()
#
#   class EditImage:
#    def addtools()
#    def removetools()
####################################################
