import slack
import json
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
from threading import Thread
import iclasses

# Slack secret vars. Temporarily hardcode. Change it later.
SLACK_TOKEN = "xoxb-2663624307237-2669072106326-GxwWg2d9zXB7dIdMdWdn5K2r"
SIGNING_SEC = "ab0a7347e231932a03c23e31ace47fc9"

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

    usr = iclasses.GetImages(username, parent_dir)

    client.chat_postMessage(channel="#test", text=usr.imgs)
    return Response(), 200


@app.route('/build', methods=['POST'])
def buildpush():

    # Convert input to list as inputcheck() needs only lists to sanitize the input
    data = request.form
    username = data.get('user_id')
    tools = data.get('text')
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
    build = iclasses.ManageImage(clean_username, clean_tools, image_name, parent_dir, dest_file)

    # Slack expects a 200 OK within 3 seconds of a slash command. If not, it'll result in a
    # "Timeout was reached" error.
    # To overcome this, we send a temporary response for eg. saying "Loading" and continue
    # our building process simultaneously as a thread.

    t1 = Thread(target=send_response, args=(build,))
    t1.start()

    client.chat_postMessage(channel="#test", text="*Building image*")

    return Response(), 200

def send_response(build):

    build.buildpush()

    # The pull_link will be set to an empty string if the building of the image failed for any reason.
    # Should see if it can be improved by handing other types of possible errors and by making the errors
    # more abstract.

    if build.pull_link == "":
        error_message = "There's some error installing the tools.\n" + "```" + build.status + "```"
        client.chat_postMessage(channel="#test", text=error_message)
    else:
        build_result = "*Built and Pushed the image*\n" + "_Image Name:_ " + build.image_name + "\n" + "_Pull Command:_ " + "docker pull " + build.pull_link
        client.chat_postMessage(channel="#test", text=build_result)


# Start your app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
