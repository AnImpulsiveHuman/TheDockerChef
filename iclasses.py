import os
import re
import json
import docker
import requests
from dotenv import load_dotenv
from coolname import generate_slug

load_dotenv()

DOCKER_MAIL = os.getenv('DOCKER_MAIL')
DOCKER_PASS = os.getenv('DOCKER_PASS')


def help_all():
    help_message = """
    *Available commands:*\n
    `/build <tool1,tool2,tool3...>`
    - _Build and Push an image with all the specified tools_\n
    `/rmi <image>`
    - _Remove the specified image_\n
    `/add <image> <tool1,tool2,tool3...>`
    - _Add the tools to the image_\n
    `/rmtool <image> <tool1,tool2,tool3...>`
    - _Remove the tools from the image_\n
    `/images`
    - _Lists all the images_\n
    `/info <image>`
    - _Gives additional info about the image_
    """
    return help_message


def inputcheck(words):
    """
    This is to sanitize user input.
    This removes anything that does not match the regex
    Only a-z A-z 0-9 - _ allowed
    """
    pattern = r'[^a-zA-Z0-9-_]'
    clean_word = [re.sub(pattern, '', word) for word in words]
    return clean_word


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
        with open(self.dest_file, "w") as dest:
            dest.write(modified_run)

        self.status = "Created Dockerfile"

        # Writes additional info like the tools etc to a ".info" file.
        # Should replace this way of keeping track by using a DB later.

        info_file = self.dest_file + ".info"
        info_dict = {}
        info_dict.setdefault("tools", self.tools)

        # Should handle the error. One error faced - expects 1 positional argument but 2 found

        json.dump(info_dict, open(info_file, 'w'))

        self.status = "Created info file. You can get more info on the image using \"?/info <image>\""


class ManageImage:

        # Set default arguments as not all the arguments are required by all the methods

    def __init__(self, username="", parent_dir="", image_name="", tools="", dest_file=""):
        self.username = username
        self.tools = tools
        self.parent_dir = parent_dir
        self.dest_file = dest_file
        self.status = ""
        self.image_name = image_name
        self.imgs = "*Your Images:*\n"
        self.info = "*Info: *\n"
        self.pull_link = "everythingtogold/gold:" + self.image_name

    def buildpush(self):
        """
        This method builds, tags and pushes the image.
        """
        dockerfile_path = self.parent_dir + "/" + self.username

        client = docker.from_env()
        print(client.login("everythingtogold", DOCKER_PASS, DOCKER_MAIL))

        try:
            print(client.images.build(path=dockerfile_path, dockerfile=self.image_name, tag=self.pull_link, rm=True))
        except docker.errors.BuildError as e:
            self.pull_link = ""
            os.remove(self.dest_file)
            os.remove(self.dest_file + ".info")
            self.status = str(e)

        print(client.images.push(repository="everythingtogold/gold", tag=self.image_name))
        self.status

    def remove_images(self):

        # Deleting the image locally

        client = docker.from_env()
        print(client.login("everythingtogold", DOCKER_PASS, DOCKER_MAIL))
        print(client.images.remove(self.pull_link))
        self.status = "Removed image locally"

        # Delete the image from Dockerhub

        docker_id = "everythingtogold"
        repo = "gold"

        dockerhub_url = "https://hub.docker.com/v2/repositories/" + docker_id + "/" + repo + "/tags/" + self.image_name + "/"

        # Change this to use requests module instead of using the os module

        token_cmd = "HUB_TOKEN=$(curl -s -H \"Content-Type: application/json\" -X POST -d \'{\"username\": \"everythingtogold\", \"password\": \"View your organizations\"}\' https://hub.docker.com/v2/users/login/ | jq -r .token)"
        #token_cmd = token_cmd.replace("username", docker_id)
        #token_cmd = token_cmd.replace("password", DOCKER_PASS)

        remove_cmd = "curl -i -X DELETE -H \"Accept: application/json\" -H \"Authorization: JWT $HUB_TOKEN\" " + dockerhub_url

        os.system(token_cmd)
        os.system(remove_cmd)

        # Deleting the dockerfile and the info file

        dockerfile = self.parent_dir + "/" + self.username + "/" + self.image_name
        info_file = dockerfile + ".info"
        os.remove(dockerfile)
        os.remove(info_file)

        self.status = "*Removed the image*"

    def get_images(self):
        """
        This lists all the images of the user. This gets all the Dockerfile names, i.e all images and
        stores them in a dictionary and uses a counter variable as the key.
        """

    # Should change to get the list of images from the remote repo.

        ctr = 1
        try:
            for file in os.listdir(self.parent_dir + "/" + self.username):
                if not file.endswith(".info"):
                    self.imgs = self.imgs + str(ctr) + ". " + file + "\n"
                    ctr = ctr + 1
            return self.imgs
        except FileNotFoundError:
            self.imgs = "No images. Use \"/build\" to start building an image."

    def get_info(self):
        """
        This gives additional info on an image.
        """

        info_file_path = self.parent_dir + "/" + self.username + "/" + self.image_name + ".info"

        try:
            info_dict = json.load(open(info_file_path))
            for key in info_dict:
                self.info = self.info + key + ": " + info_dict[key] + "\n"
        except FileNotFoundError:
            self.info = "*Oops, image not found*"

class EditImage:

    def __init__(self, username, image_name, removetools_list, parent_dir):
        self.username = username
        self.image_name = image_name
        self.removetools_list = removetools_list
        self.parent_dir = parent_dir
        self.dockerfile = ""
        self.status = ""

    def removetools(self):

        # Creates the updated dockerfile without the unwanted tools.
        # Should take of error handling when the given image is not already installed.

        self.dockerfile = self.parent_dir + "/" + self.username + "/" + self.image_name

        print(self.image_name)
        # print(type(image_name))

        old_dockerfile = open(self.dockerfile).readlines()
        for i, line in enumerate(old_dockerfile):
            if line.startswith("RUN"):
                runline = line.split("&&")

                pattern = "apt-get install -y"

                # Removes the unwanted tools from the original RUN Instr

                for run in runline:
                    t = re.sub(pattern, '', run)
                    if t.strip(" ") in self.removetools_list:
                        runline.remove(run)

                # Should join or else cant join this with our dockerfile as this is list.

                old_dockerfile[i] = "&&".join(runline)

        # writing the new contents to the dockerfile

        updated_dockerfile = "".join(old_dockerfile)
        with open(self.dockerfile, 'w') as updated:
            updated.write(updated_dockerfile)

        # Remove the removed tools from the info file

        info_dict = json.load(open(self.dockerfile + ".info"))
        tools_list = info_dict['tools'].split(",")

        for tool in tools_list:
            if tool in self.removetools_list:
                tools_list.remove(tool)

        tools = ",".join(tools_list)
        info_dict.update({'tools': tools})
        json.dump(info_dict, open(self.dockerfile + ".info", 'w'))

        self.status = "Removed tools"

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
