//
// Created by Nicholas Lao on 2019-01-02.
//

#ifndef IPERFER_AUX_H
#define IPERFER_AUX_H

#include <errno.h>
#include <sys/wait.h>
#include <netdb.h>

/* Calling waitpid() may overwrite errno */
void sigchld_handler(int signal) {
    int saved_errno = errno;
    while (waitpid(-1, nullptr, WNOHANG) > 0);
    errno = saved_errno;
}

void *get_in_addr(struct sockaddr *sa) {
    return sa->sa_family == AF_INET
           ? (void *) &(((struct sockaddr_in *) sa)->sin_addr)
           : (void *) &(((struct sockaddr_in6 *) sa)->sin6_addr);
}


#endif // IPERFER_AUX_H
