# xml server config
global __server__
global __port__

__server__ = "0.0.0.0"
__port__ = 9854


# Set the server type
#
#   Options are:
#       single_threaded     - run a single thread server
#       threaded            - run a threaded server, a new thread is created on each connection
#       thread_pool         - run a threaded server, a thread_pool is maintained to handle queued requests
__type__ = "thread_pool"
__poolsize__ = 16        #thread pool size
