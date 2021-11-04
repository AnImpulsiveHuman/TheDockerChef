import os
import slack
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
from threading import Thread
import iclasses

load_dotenv()

# Slack secret tokens from .env
SLACK_TOKEN = os.getenv('SLACK_TOKEN')
SIGNING_SEC = os.getenv('SIGNING_SEC')

parent_dir = "allfiles/"

app = Flask(__name__)

slack_event_adapter = SlackEventAdapter(SIGNING_SEC, "/slack/events", app)

client = slack.WebClient(token=SLACK_TOKEN)
client.chat_postMessage(channel="#test", text="We are open!")


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    text = event.get('text')
    if text == "hello chef!":
        client.chat_postMessage(channel="#test", text="Hello from the Chef")


@app.route('/images', methods=['POST'])
def images():
    data = request.form
    username = data.get('user_id')
    print(username)

    usr = iclasses.ManageImage(username, parent_dir)
    images = usr.get_images()

    client.chat_postMessage(channel="#test", text=usr.imgs)
    return Response(), 200


@app.route('/info', methods=['POST'])
def info():
    data = request.form
    text = data.get('text')
    text_list = text.split(" ")  # to split the arguments into a list
    username = data.get('user_id')

    clean_username_list = iclasses.inputcheck(username.split())
    clean_image_name_list = iclasses.inputcheck(text_list[0])

    # Convert the clean inputs back to strings as CreateDockerfile needs only strings
    clean_username = "".join(clean_username_list)
    clean_image_name = "".join(clean_image_name_list)

    manage_obj = iclasses.ManageImage(clean_username, parent_dir, clean_image_name)
    manage_obj.get_info()

    client.chat_postMessage(channel="#test", text=manage_obj.info)

    return Response(), 200


@app.route('/help', methods=['POST'])
def help_all():
    help_message = iclasses.help_all()

    client.chat_postMessage(channel="#test", text=help_message)

    return Response(), 200


@app.route('/build', methods=['POST'])
def buildpush():

    data = request.form
    username = data.get('user_id')
    tools = data.get('text')

    # Convert input to list as inputcheck() needs only lists to sanitize the input
    clean_username_list = iclasses.inputcheck(username.split())
    clean_tools_list = iclasses.inputcheck(tools.split(","))

    # Convert the clean inputs back to strings as CreateDockerfile needs only strings
    clean_username = "".join(clean_username_list)
    clean_tools = ",".join(clean_tools_list)

    # Creates the dockerfile
    user = iclasses.CreateDockerfile(clean_username, clean_tools, parent_dir)
    user.fileparse()
    dockerfile_result = "*Dockerfile created*\n" + "_Tools:_ " + tools + "\n"
    client.chat_postMessage(channel="#test", text=dockerfile_result)

    dest_file = user.dest_file
    image_name = user.dockerfile_name

    # Build and push the image
    build = iclasses.ManageImage(clean_username, parent_dir, image_name, clean_tools, dest_file)

    # Slack expects a 200 OK within 3 seconds of a slash command. If not, it'll result in a
    # "Timeout was reached" error.
    # To overcome this, we send a temporary response for eg. saying "Loading" and continue
    # our building process simultaneously as a thread.

    t1 = Thread(target=send_response, args=(build,))
    t1.start()

    client.chat_postMessage(channel="#test", text="*Building image*")

    return Response(), 200

def send_response(build):

    # Should improve.
    # The buildpush() methods calls all the other needed class methods within itself.
    # Instead of calling all methods automatically inside the class methods,
    # we can call each method separately and send status messages after each method.
    # This might make the wait time seem short because of acknowledgments
    # being sent constantly until the final acknowledgment gets sent.
    # Kinda like a loading screen.

    build.buildpush()

    # The pull_link will be set to an empty string if the building of the image failed for any reason.
    # Should see if it can be improved by handling other types of possible errors and by making the errors
    # more abstract.

    if build.pull_link == "":
        error_message = "There's some error installing the tools.\n" + "```" + build.status + "```"
        client.chat_postMessage(channel="#test", text=error_message)
    else:
        pull_cmd = "_Pull Command:_\n" + "docker pull " + build.pull_link
        build_result = "*Built and Pushed the image*\n" + "_Image Name:_ " + build.image_name + "\n"

        client.chat_postMessage(channel="#test", text=build_result)
        client.chat_postMessage(channel="#test", text=pull_cmd)


@app.route('/remove', methods=['POST'])
def rmi():
    data = request.form
    text = data.get('text')
    text_list = text.split(" ")  # to split the arguments into a list

    clean_username_list = iclasses.inputcheck(data.get('user_id'))
    clean_image_name_list = iclasses.inputcheck(text_list[0])

    clean_username = "".join(clean_username_list)
    clean_image_name = "".join(clean_image_name_list)

    manage_obj = iclasses.ManageImage(clean_username, parent_dir, clean_image_name)
    manage_obj.remove_images()

    client.chat_postMessage(channel="#test", text=manage_obj.status)

    return Response(), 200

@app.route('/rmtool', methods=['POST'])
def rmtool():
    data = request.form
    text = data.get('text')
    text_list = text.split(" ")  # to split the arguments into a list

    clean_username_list = iclasses.inputcheck(data.get('user_id'))
    clean_image_name_list = iclasses.inputcheck(text_list[0])
    clean_removetools_list = iclasses.inputcheck(text_list[1:])

    clean_username = "".join(clean_username_list)
    clean_image_name = "".join(clean_image_name_list)

    edit = iclasses.EditImage(clean_username, clean_image_name, clean_removetools_list, parent_dir)
    edit.removetools()

    client.chat_postMessage(channel="#test", text=edit.status)

    dockerfile = edit.dockerfile
    build = iclasses.ManageImage(clean_username, parent_dir, clean_image_name, clean_removetools_list, dockerfile)

    t1 = Thread(target=send_response, args=(build,))
    t1.start()

    client.chat_postMessage(channel="#test", text="*Pushing the image*")

    return Response(), 200

def send_response(build):

    build.buildpush()

    if build.pull_link == "":
        error_message = "There's some error installing the tools.\n" + "```" + build.status + "```"
        client.chat_postMessage(channel="#test", text=error_message)
    else:
        build_result = "*Built and Pushed the image*\n" + "_Image Name:_ " + build.image_name + "\n" + "_Pull Command:_ " + "docker pull " + build.pull_link
        client.chat_postMessage(channel="#test", text=build_result)


# Start your app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")