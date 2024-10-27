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

# Defining the constants
MAX_THREAD_COUNT = 4
GITHUB_API = "api.github.com"
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

    print(files)


get_repository_contents()
