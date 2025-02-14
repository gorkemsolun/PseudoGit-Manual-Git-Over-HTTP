# Görkem Kadir Solun 22003214


import base64
import json
import os
import socket
import ssl
import sys
import threading

import pandas as pd

# Defining the constants
MAX_THREAD_COUNT = 4
GITHUB_API = "api.github.com"
GITHUB_API_RAW = "raw.githubusercontent.com"
GITHUB_HOST = "github.com"
GITHUB_PORT = 443
BUFFER_SIZE = 4096
GITHUB_URL = "https://api.github.com"

# Defining the global variables
access_token = ""
username = ""
repository = ""
branch = "main"


# Function to create a secure socket
def create_secure_socket(server_hostname=GITHUB_API):
    """
    Function to create a secure socket

    :param server_hostname: The server hostname

    :return: The secure socket object
    """

    # Create a new SSL context
    context = ssl.create_default_context()

    # Create a new socket
    secure_socket = context.wrap_socket(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM),
        server_hostname=server_hostname,
    )

    return secure_socket


def send_request(secure_socket, host, port, request):
    """
    Function to send an HTTP request to the server and receive the response

    :param socket: The socket object
    :param host: The host address
    :param port: The port number
    :param request: The HTTP request

    :return: The response from the server
    """

    # Connect to the server
    secure_socket.connect((host, port))
    # Send the request
    secure_socket.sendall(request.encode())

    # Receive the response data in chunks
    response = b""
    while True:
        response_chunk = secure_socket.recv(BUFFER_SIZE)
        if not response_chunk:
            break
        response += response_chunk

    # get the response header
    response_header = response.split(b"\r\n\r\n")[0]

    # get the response body
    response_body = response.split(b"\r\n\r\n")[1]

    # get the status code
    status_code = response_header.split(b"\r\n")[0].split(b" ")[1]

    # get the response body as a string
    try:
        response_body_str = response_body.decode("utf-8")
    except:
        response_body_str = ""

    return {
        "status_code": status_code,
        "response_body": response_body_str,
        "response_body_bytes": response_body,
        "response_header": response_header,
    }


def get_file_from_github(file_name, directory="pseudo_git_downloads", parallel_count=4):
    """
    Function to get a file from GitHub

    :param file_name: The name of the file
    :param directory: The directory to save the file
    :param parallel_count: The number of parallel threads to download the file
    :param file_name: The name of the output file

    :return: None
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/contents/{file_name} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = json.loads(response["response_body"])
    content = response_body["content"]

    # if the file exists in the directory and does have the same size, do not download it again
    split_path = file_name.split("/")
    new_directory_path = directory
    for path in split_path[:-1]:
        new_directory_path += f"/{path}"
    if split_path[-1] in os.listdir(new_directory_path):
        file_size = os.path.getsize(directory + "/" + file_name)
        if file_size == response_body["size"]:
            print(f"File {file_name} already exists in the directory")
            return

    print(f"Downloading file {file_name}")

    # If the response_body is not empty write the content to the file
    if content:
        content = base64.b64decode(content)
        with open(f"{directory}/{file_name}", "wb") as file:
            file.write(content)

        return

    # Get the file size and the download URL
    file_size = response_body["size"]
    download_url = response_body["download_url"]

    # Calculate the chunk size
    chunk_size = file_size // parallel_count

    # Create the threads
    threads = []
    for i in range(parallel_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size - 1 if i < parallel_count - 1 else file_size
        thread = threading.Thread(
            target=download_file_chunk,
            args=(download_url, start, end, f"{file_name}_{i}", directory),
        )
        threads.append(thread)
        thread.start()

    # Wait for the threads to finish
    for thread in threads:
        thread.join()

    # Concatenate the chunks
    with open(f"{directory}/{file_name}", "wb") as file:
        for i in range(parallel_count):
            with open(f"{directory}/{file_name}_{i}", "rb") as chunk_file:
                file.write(chunk_file.read())

    # Remove the chunk files
    for i in range(parallel_count):
        os.remove(f"{directory}/{file_name}_{i}")


def download_file_chunk(url, start, end, file_name, directory):
    """
    Function to download a file chunk

    :param url: The URL of the file
    :param start: The start byte of the chunk
    :param end: The end byte of the chunk
    :param file_name: The name of the output file
    :param directory: The directory to save the file
    """

    # Create a secure socket
    secure_socket = create_secure_socket(GITHUB_API_RAW)

    # Construct the request
    request = f"GET {url} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API_RAW}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += f"Range: bytes={start}-{end}\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API_RAW, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = response["response_body_bytes"]

    # Write the content to the file
    with open(f"{directory}/{file_name}", "wb") as file:
        file.write(response_body)


def get_repository_contents(path=""):
    """
    Function to get the contents of the repository

    :return: The list of files in the repository and their types
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/contents"
    if path:
        request += f"/{path}"
    request += f" HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = json.loads(response["response_body"])

    # Get the list of files
    files = [[file["path"], file["type"]] for file in response_body]

    return files


def download_files(files, directory="pseudo_git_downloads", parallel_count=4):
    """
    Function to download files from GitHub

    :param files: The list of files to download
    """

    threads = []

    for file in files:
        # If the file is a directory, download the files in the directory recursively
        if file[1] == "dir":
            split_path = file[0].split("/")
            new_directory_path = directory
            for path in split_path[:-1]:
                new_directory_path += f"/{path}"

            # Create the directory if it does not exist
            if split_path[-1] not in os.listdir(new_directory_path):
                print(f"Creating directory {split_path[-1]}")
                os.mkdir(f"{directory}/{file[0]}")

            sub_files = get_repository_contents(file[0])
            download_files(sub_files, directory, parallel_count)
            continue

        # Create a new thread to download the file
        thread = threading.Thread(
            target=get_file_from_github, args=(file[0], directory, parallel_count)
        )
        threads.append(thread)
        thread.start()

        if len(threads) >= MAX_THREAD_COUNT:
            for thread in threads:
                thread.join()
            threads = []

    for thread in threads:
        thread.join()


def get_latest_commit_sha():
    """
    Function to get the latest commit SHA

    :return: The latest commit SHA
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/branches/{branch} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = json.loads(response["response_body"])
    sha = response_body["commit"]["sha"]

    return sha


def get_file_sha(file_name):
    """
    Function to get the SHA of a file

    :param file_name: The name of the file

    :return: The SHA of the file
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/contents/{file_name} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = json.loads(response["response_body"])

    # If the response_body is empty return None as the SHA
    if not response_body or "sha" not in response_body:
        return None

    sha = response_body["sha"]

    return sha


def create_branch(branch_name):
    """
    Function to create a new branch

    :param branch_name: The name of the new branch
    """

    # Get the latest commit SHA
    sha = get_latest_commit_sha()

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"POST /repos/{username}/{repository}/git/refs HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Connection: close\r\n"
    request += f"Content-Length: {len(json.dumps({'ref': f'refs/heads/{branch_name}', 'sha': sha}))}\r\n\r\n"
    request += json.dumps({"ref": f"refs/heads/{branch_name}", "sha": sha})

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"201":
        print(f"Branch {branch_name} created successfully")
    else:
        print(f"Failed to create branch {branch_name}")


def delete_branch(branch_name):
    """
    Function to delete a branch

    :param branch_name: The name of the branch to delete
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"DELETE /repos/{username}/{repository}/git/refs/heads/{branch_name} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"204":
        print(f"Branch {branch_name} deleted successfully")
    else:
        print(f"Failed to delete branch {branch_name}")


def push_changes(file_name, branch_name, message="Pushed changes"):
    """
    Function to push the changes to the repository

    :param file_name: The name of the file to push
    :param branch_name: The name of the branch to push to
    """

    # Get the file SHA
    sha = get_file_sha(file_name)

    # Read the file content
    with open(file_name, "rb") as file:
        content = file.read()

    # Encode the file content
    content = base64.b64encode(content).decode()

    content_json = None
    if sha is None:
        content_json = json.dumps(
            {"message": message, "content": content, "branch": branch_name}
        )
    else:
        content_json = json.dumps(
            {"message": message, "content": content, "branch": branch_name, "sha": sha}
        )

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"PUT /repos/{username}/{repository}/contents/{file_name} HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Connection: close\r\n"
    request += f"Content-Length: {len(content_json)}\r\n\r\n"
    request += f"{content_json}"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"200":
        print(
            f"Changes pushed successfully to branch {branch_name} and file {file_name} updated"
        )
    elif response["status_code"] == b"201":
        print(
            f"Changes pushed successfully to branch {branch_name} and file {file_name} created"
        )
    else:
        print(f"Failed to push changes to branch {branch_name}")


def create_pull_request(title, body, head, base):
    """
    Function to create a pull request

    :param title: The title of the pull request
    :param body: The body of the pull request
    :param head: The head branch
    :param base: The base branch
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"POST /repos/{username}/{repository}/pulls HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Connection: close\r\n"
    request += f"Content-Length: {len(json.dumps({'title': title, 'body': body, 'head': head, 'base': base}))}\r\n\r\n"
    request += json.dumps({"title": title, "body": body, "head": head, "base": base})

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"201":
        print(f"Pull request created successfully")
    else:
        print(f"Failed to create pull request")


def list_open_pull_requests():
    """
    Function to list the open pull requests

    :return: The list of open pull requests
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/pulls HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    response_body = json.loads(response["response_body"])

    # Return the list of pull requests' numbers
    list_of_pull_requests = [
        [pull_request["number"], pull_request["title"]]
        for pull_request in response_body
    ]

    return pd.DataFrame(list_of_pull_requests, columns=["Pull Request Number", "Title"])


def merge_pull_request(pull_request_number):
    """
    Function to merge a pull request

    :param pull_request_number: The number of the pull request
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"PUT /repos/{username}/{repository}/pulls/{pull_request_number}/merge HTTP/1.1\r\n"
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Connection: close\r\n\r\n"

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"200":
        print(f"Pull request merged successfully")
    else:
        print(f"Failed to merge pull request")


def close_pull_request(pull_request_number):
    """
    Function to close a pull request

    :param pull_request_number: The number of the pull request
    """

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = (
        f"PATCH /repos/{username}/{repository}/pulls/{pull_request_number} HTTP/1.1\r\n"
    )
    request += f"Host: {GITHUB_API}\r\n"
    request += f"Authorization: token {access_token}\r\n"
    request += "User-Agent: PseudoGit\r\n"
    request += "Accept: application/vnd.github.v3+json\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Connection: close\r\n"
    request += f"Content-Length: {len(json.dumps({'state': 'closed'}))}\r\n\r\n"
    request += json.dumps({"state": "closed"})

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"200":
        print(f"Pull request closed successfully")
    else:
        print(f"Failed to close pull request")


def main():

    print(
        """Usage of the PseudoGit:
        Core commands:
        python PseudoGit.py clone <username>/<repository_name> <parallel_count>
        python PseudoGit.py branch <username>/<repository_name> <branch_name>
        python PseudoGit.py upload <username>/<repository_name> <branch_name> <file_name>
        python PseudoGit.py create-pr <username>/<repository_name> <branch_name>
        python PseudoGit.py list-pr <username>/<repository_name>
        python PseudoGit.py merge-pr <username>/<repository_name> <pr_number>
        
        Additional commands:
        python PseudoGit.py delete-branch <username>/<repository_name> <branch_name>
        python PseudoGit.py close-pr <username>/<repository_name> <pr_number>
        
        Additionally, you need to enter your access token when prompted.
        """
    )

    if len(sys.argv) < 3:
        print("Invalid number of arguments")
        return

    global access_token
    if not access_token:
        access_token = input("Enter your access token: ")

    global username
    global repository
    command = sys.argv[1]
    username, repository = sys.argv[2].split("/")

    if command == "clone":
        parallel_count = int(sys.argv[3]) if len(sys.argv) == 4 else 4
        files = get_repository_contents()
        if repository not in os.listdir():
            os.mkdir(repository)
        download_files(files, repository, parallel_count)

    if command == "branch":
        branch_name = sys.argv[3]
        create_branch(branch_name)

    if command == "delete-branch":
        branch_name = sys.argv[3]
        delete_branch(branch_name)

    if command == "upload":
        branch_name = sys.argv[3]
        file_name = sys.argv[4]
        push_changes(file_name, branch_name)

    if command == "create-pr":
        branch_name = sys.argv[3]
        create_pull_request(
            "Pull Request Title", "Pull Request Body", branch_name, "main"
        )

    if command == "close-pr":
        pull_request_number = int(sys.argv[3])
        close_pull_request(pull_request_number)

    if command == "list-pr":
        open_pull_requests = list_open_pull_requests()
        print("Open pull requests:")
        print(open_pull_requests)

    if command == "merge-pr":
        pull_request_number = int(sys.argv[3])
        merge_pull_request(pull_request_number)


if __name__ == "__main__":
    main()
