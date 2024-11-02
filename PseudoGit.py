"""
In this assignment, titled "PseudoGit," you are tasked with building a simplified version of the Git functionality for interacting with GitHub, but with unique restrictions.
You’re required to create a Python program that can clone a GitHub repository, make modifications, and submit a pull request for those changes.
Importantly, this assignment prohibits the use of any git-related libraries or HTTP client libraries, including commonly used modules like Python's `requests` and HTTP client APIs. 
Instead, all communication with GitHub must be managed at a lower level, using only socket programming. This is designed to help you learn about the HTTP protocol fundamentals 
and socket programming while deepening your understanding of how git operations function at a network level.

The assignment is divided into two main tasks. The first task is to clone a repository from GitHub. Typically, this is done with a simple `git clone` command, but here, 
you’ll be writing the functionality from scratch using HTTP GET requests to access the repository files. This task involves several steps, including creating a GitHub account, 
forking the specified repository, and generating a personal access token for authentication. You’ll need to request the contents of the repository, download each file individually, 
and handle the special case of large files (greater than 1 MB) by downloading them in parallel using multiple threads. 
This parallel download functionality is controlled by a command-line argument that specifies the number of concurrent threads.

The second task is to implement a "pull request" workflow. After cloning and modifying the repository, you’ll use HTTP requests to create a new branch, commit your changes, 
and push the updated file to this branch. Subsequently, you’ll create a pull request from this new branch to the main branch, and finally, list and merge the pull request. 
Each of these steps involves HTTP requests to specific GitHub REST API endpoints, which you’ll call manually through your program, using only socket-based communication. 
This task tests your ability to coordinate a complex sequence of API interactions over HTTP to mimic git’s pull request process.

Your program will be a command-line application named "PseudoGit," capable of executing various commands to clone, create branches, upload files, and handle pull requests. 
The assignment also includes detailed specifications for naming conventions, required output, and submission formats, emphasizing precision and adherence to guidelines. 
Lastly, you’ll prepare a concise report, explaining your program’s structure and main functions, without exceeding five pages. This project offers an in-depth experience in network programming, 
low-level HTTP communication, and threading, all framed within the context of a fundamental software engineering tool—git.

"""

import base64
import json
import os
import socket
import ssl
import sys
import threading
import time

import chardet

# Defining the constants
MAX_THREAD_COUNT = 4
GITHUB_API = "api.github.com"
GITHUB_API_RAW = "raw.githubusercontent.com"
GITHUB_HOST = "github.com"
GITHUB_PORT = 443
BUFFER_SIZE = 4096
GITHUB_URL = "https://api.github.com"

# Defining the global variables
access_token = "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"
username = "gorkemsolun"
repository = "PseudoGit"
branch = "main"


# Function to get the access token
def get_access_token():
    global access_token
    access_token = input("Enter your access token: ")


# Function to get the username
def get_username():
    global username
    username = input("Enter your username: ")


# Function to get the repository
def get_repository():
    global repository
    repository = input("Enter the repository: ")


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
    response_body_str = response_body.decode("utf-8")

    return {
        "status_code": status_code,
        "response_body": response_body_str,
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

    # check if the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

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
        end = (i + 1) * chunk_size if i < parallel_count - 1 else file_size
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
    response_body = response["response_body"]

    # Write the content to the file
    with open(f"{directory}/{file_name}", "wb") as file:
        file.write(response_body.encode())


def get_repository_contents():
    """
    Function to get the contents of the repository

    :return: The list of files in the repository
    """

    if not access_token:
        get_access_token()

    if not username:
        get_username()

    if not repository:
        get_repository()

    # Create a secure socket
    secure_socket = create_secure_socket()

    # Construct the request
    request = f"GET /repos/{username}/{repository}/contents HTTP/1.1\r\n"
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
    files = [file["name"] for file in response_body]

    return files


def download_files(files, directory="pseudo_git_downloads"):
    """
    Function to download files from GitHub

    :param files: The list of files to download
    """

    threads = []

    for file in files:
        thread = threading.Thread(target=get_file_from_github, args=(file, directory))
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


def push_changes(file_name, branch_name):
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
    request += f"Content-Length: {len(json.dumps({'message': 'Add new file', 'content': content, 'branch': branch_name, 'sha': sha}))}\r\n\r\n"
    request += json.dumps(
        {
            "message": "Add new file",
            "content": content,
            "branch": branch_name,
            "sha": sha,
        }
    )

    # Send the request and receive the response
    response = send_request(secure_socket, GITHUB_API, GITHUB_PORT, request)

    # Close the socket
    secure_socket.close()

    # Parse the response
    if response["status_code"] == b"200":
        print(f"Changes pushed successfully to branch {branch_name}")
    else:
        print(f"Failed to push changes to branch {branch_name}")


def main():
    # Get the repository contents and download small files
    """repo_contents = get_repository_contents()
    print("Repository contents:", repo_contents)
    download_files(repo_contents)"""

    """ create_branch("new_branch")
    time.sleep(5)
    push_changes("deneme.py", "new_branch")
    time.sleep(5)
    delete_branch("new_branch") """

    push_changes("PseudoGit.py", "main")


if __name__ == "__main__":
    main()
