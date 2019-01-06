#include "aux.h"
#include <iostream>
#include <map>
#include <string>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <signal.h>

#define BACKLOG 10     // Pending connections the queue will hold
#define CHUNKSIZE 1000 // Number of bytes we transmit at once

void runInServerMode(const std::string &);

void runInClientMode(const std::string &host, const std::string &port, int);

int main(int argc, const char **argv) {
    /* Resolve the arguments */
    std::map<std::string, std::string> args;
    bool argData = false;

    for (int i = 1; i < argc; i++) {
        if (argv[i][0] == '-') {
            args[argv[i]] = "";
            argData = true;
        } else if (!argData) {
            std::cerr << "Error: missing or additional arguments" << std::endl;
            return -1;
        } else {
            args[argv[i - 1]] = argv[i];
            argData = false;
        }
    }

    bool server_mode = args.find("-s") != args.end();
    bool client_mode = args.find("-c") != args.end();
    if (!(server_mode ^ client_mode)) {
        std::cerr << "Error: missing or additional arguments" << std::endl;
        return -1;
    }

    if (server_mode) {
        if (args.size() != 2 || args.find("-p") == args.end() || args["-p"].empty()) {
            std::cout << "Error: missing or additional arguments" << std::endl;
            return -1;
        }
        runInServerMode(args["-p"]);
    } else {
        std::string host = args["-h"];
        std::string port = args["-p"];
        std::string time = args["-t"];

        if (args.size() != 4 || host.empty() || port.empty() || time.empty()) {
            std::cerr << "Error: missing or additional arguments" << std::endl;
            return -1;
        }
        runInClientMode(host, port, stoi(time));
    }
    return 0;
}


void runInServerMode(const std::string &port) {
    if (stoi(port) < 1024 || stoi(port) > 65535) {
        std::cerr << "Error: port number must be in the range 1024 to 65535" << std::endl;
        exit(EXIT_FAILURE);
    }

    int status;
    int yes = 1;
    int socket_fd, new_fd;
    struct sigaction sa;
    struct addrinfo *serverInfo, *p, hints;
    struct sockaddr_storage cliAddr;
    socklen_t sin_size = sizeof cliAddr;
    char str[INET6_ADDRSTRLEN];

    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    status = getaddrinfo(nullptr, port.c_str(), &hints, &serverInfo);
    if (status != 0) {
        std::cerr << "Error: getaddrinfo() failed: " << gai_strerror(status) << std::endl;
        exit(EXIT_FAILURE);
    }

    /* Loop through all the results and bind to the first available */
    for (p = serverInfo; p != nullptr; p = p->ai_next) {
        if ((socket_fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) == -1) {
            perror("Warning: socket() failed while trying\n");
            continue;
        }

        /* Allow the program to reuse the port */
        if (setsockopt(socket_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes) == -1) {
            perror("Error: setsockopt() failed\n");
            exit(EXIT_FAILURE);
        }

        if (bind(socket_fd, p->ai_addr, p->ai_addrlen) == -1) {
            close(socket_fd);
            perror("Warning: bind() failed while trying\n");
            continue;
        }

        break;
    }

    freeaddrinfo(serverInfo);
    if (p == nullptr) {
        perror("Error: bind() failed\n");
        exit(EXIT_FAILURE);
    }

    if (listen(socket_fd, BACKLOG) == -1) {
        perror("Error: listen() failed\n");
        exit(EXIT_FAILURE);
    }

    sa.sa_handler = sigchld_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    if (sigaction(SIGCHLD, &sa, nullptr) == -1) {
        perror("Error: sigaction() failed\n");
        exit(EXIT_FAILURE);
    }

    printf("Waiting for connections on port %s ...\n", port.c_str());

    while(true) {
        new_fd = accept(socket_fd, (struct sockaddr *)&cliAddr, &sin_size);
        if (new_fd == -1) {
            perror("Error: accept() failed\n");
            continue;
        }

        inet_ntop(cliAddr.ss_family, get_in_addr((struct sockaddr *)&cliAddr), str, sizeof str);
        printf("Received connection from %s\n", str);

        if (!fork()) {
            /* Child process doesn't need the listener */
            close(socket_fd);
            if (send(new_fd, "Hello, world!", 13, 0) == -1)
                perror("send");
            close(new_fd);
            exit(EXIT_SUCCESS);
        }
        close(new_fd);
    }
}


void runInClientMode(const std::string &host, const std::string &port, int time) {
    if (stoi(port) < 1024 || stoi(port) > 65535) {
        std::cerr << "Error: port number must be in the range 1024 to 65535" << std::endl;
        exit(EXIT_FAILURE);
    }

    int status;
    int socket_fd;
    int numBytes;
    char buf[CHUNKSIZE];
    struct addrinfo hints, *serverInfo, *p;
    char str[INET6_ADDRSTRLEN];

    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    status = getaddrinfo(nullptr, port.c_str(), &hints, &serverInfo);
    if (status != 0) {
        std::cerr << "Error: getaddrinfo() failed: " << gai_strerror(status) << std::endl;
        exit(EXIT_FAILURE);
    }

    /* Loop through all the results and bind to the first available */
    for(p = serverInfo; p != nullptr; p = p->ai_next) {
        if ((socket_fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) == -1) {
            perror("Warning: socket() failed while trying\n");
            continue;
        }

        if (connect(socket_fd, p->ai_addr, p->ai_addrlen) == -1) {
            close(socket_fd);
            perror("Warning: connect() failed while trying\n");
            continue;
        }

        break;
    }

    if (p == nullptr) {
        perror("Error: connect() failed\n");
        exit(EXIT_FAILURE);
    }

    inet_ntop(p->ai_family, get_in_addr(p->ai_addr), str, sizeof str);
    printf("Connecting to %s\n", str);
    freeaddrinfo(serverInfo);

    if ((numBytes = recv(socket_fd, buf, CHUNKSIZE-1, 0)) == -1) {
        perror("Warning: recv() failed\n");
        exit(EXIT_FAILURE);
    }

    buf[numBytes] = '\0';

    printf("client: received '%s'\n",buf);

    close(socket_fd);
}
