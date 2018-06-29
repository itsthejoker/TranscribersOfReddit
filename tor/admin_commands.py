from tor_core.config import Config

from typing import Any

"""
This is a manifest of methods we call for the admin command system. All methods
should have the following signatures:

    param author [String] Reddit username of the person invoking the command
    param arg    [String] The blob of text as the argument to be passed into the
                          admin command
    param svc    [Any]    An object to pass in containing the already-connected
                          resources for doing the needful.
    return       [String] The response to send to the user invoking the command
"""


def undefined_operation(author: str, arg: str, svc: Any) -> str:
    """
    This is the default action if nothing is defined in commands.json mapping

    author  -> (ignored)
    arg     -> (ignored)
    svc     -> (ignored)
    """
    # Should we instead send a response back to the user with this info?
    raise NotImplementedError("Undefined operation")


def noop(author: str, arg: str, svc: Any) -> str:
    """
    In case a command is intended not to do anything...

    author  -> (ignored)
    arg     -> (ignored)
    svc     -> (ignored)
    """
    return "Nothing to be done."


def ping(author: str, arg: str, svc: Any) -> str:
    """
    Alive checker for the bot.

    author  -> The user pinging the bot
    arg     -> (ignored)
    svc     -> (ignored)
    """
    # TODO: Extend to have every worker check in
    return "Pong!"


def process_blacklist(author: str, arg: str, svc: Any) -> str:
    """
    Essentially shadow-banning a user, as far as the bots are concerned.

    author  -> The user doing the banning
    arg     -> The username in which to ban
    svc     -> Any object that has:
                 - a redis connection at `self.redis`
                 - a requests object at `self.http`
    """
    users = arg.splitlines()
    config = Config.subreddit("TranscribersOfReddit")
    failed = {
        # "username": "reason"
    }
    succeeded = []

    for user in users:
        if config.globals.is_moderator(user):
            failed[user] = "is a moderator"

        elif svc.http.get(f"https://reddit.com/u/{user}.json").status_code == 404:
            failed[user] = "is not a valid username on Reddit"

        elif svc.redis.sadd("blacklist", user):
            succeeded.append(user)

        else:
            failed[user] = "is already blacklisted"

    out = f"Blacklist: " f"{len(failed.keys())} failed, " f"{len(succeeded)} succeeded\n"

    for user, reason in failed.items():
        out += f"\n- **{user}** {reason}"

    return out


# These are on the back burner right now. Just silently drop it
update_and_restart = noop
reload_config = noop
